import time as time_module
from datetime import datetime

from celery.exceptions import SoftTimeLimitExceeded, MaxRetriesExceededError
from sqlalchemy.orm.attributes import flag_modified

from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.services.pipeline import run_pipeline


def _append_project_log(db, project, msg: str, level: str = "info") -> None:
    logs = list(project.logs or [])
    logs.append(
        {
            "ts": datetime.utcnow().isoformat() + "Z",
            "msg": msg,
            "level": level,
        }
    )
    project.logs = logs
    flag_modified(project, "logs")


def _fmt_duration(seconds: float) -> str:
    s = int(round(seconds))
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_generation_task(self, task_id: str):
    """
    Celery task wrapper to run the full article generation pipeline in the background.
    Handles high-level Celery exceptions and db session management.
    """
    db = SessionLocal()
    try:
        run_pipeline(db, task_id)
        
    except SoftTimeLimitExceeded:
        from app.models.task import Task
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_log = "Celery task soft time limit exceeded (timeout)."
            db.commit()
            
    except Exception as exc:
        import traceback
        from app.models.task import Task
        
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.status != "failed":
            task.status = "failed"
            task.error_log = f"Worker crashed: {exc}\n{traceback.format_exc()}"
            db.commit()
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def process_site_project(self, project_id: str):
    """
    Celery task wrapper to run all pages of a site project sequentially.
    Supports resume (skips completed pages) and cooperative cancellation (stopping_requested).
    """
    db = SessionLocal()
    from app.models.project import SiteProject
    from app.models.blueprint import BlueprintPage
    from app.models.task import Task
    from app.services.site_builder import build_site
    import traceback
    import json

    project = None
    try:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if not project:
            print(f"Project {project_id} not found!")
            return

        project.status = "generating"
        db.commit()

        pages = (
            db.query(BlueprintPage)
            .filter(BlueprintPage.blueprint_id == project.blueprint_id)
            .order_by(BlueprintPage.sort_order)
            .all()
        )
        failed_pages = []
        n_pages = len(pages)

        existing_tasks = db.query(Task).filter(
            Task.project_id == project.id,
            Task.status == "completed",
        ).all()
        completed_page_ids = {str(t.blueprint_page_id) for t in existing_tasks}

        for i, page in enumerate(pages):
            if str(page.id) in completed_page_ids:
                print(f"Skipping already completed page: {page.page_title}")
                continue

            project.current_page_index = i
            db.commit()

            template = page.keyword_template
            if getattr(project, "seed_is_brand", False) and getattr(
                page, "keyword_template_brand", None
            ):
                template = page.keyword_template_brand
            keyword = template.replace("{seed}", project.seed_keyword)

            existing_task = db.query(Task).filter(
                Task.project_id == project.id,
                Task.blueprint_page_id == page.id,
                Task.status.in_(["pending", "failed"]),
            ).first()

            proj_serp = getattr(project, "serp_config", None) or {}

            if existing_task:
                new_task = existing_task
                new_task.status = "pending"
                new_task.error_log = None
                new_task.serp_config = proj_serp
                db.commit()
            else:
                new_task = Task(
                    main_keyword=keyword,
                    country=project.country,
                    language=project.language,
                    page_type=page.page_type,
                    target_site_id=project.site_id,
                    author_id=project.author_id,
                    project_id=project.id,
                    blueprint_page_id=page.id,
                    status="pending",
                    serp_config=proj_serp,
                )
                db.add(new_task)
                db.commit()
                db.refresh(new_task)

            db.refresh(project)
            if project.started_at is None:
                project.started_at = datetime.utcnow()
            _append_project_log(
                db,
                project,
                f"Starting page {i + 1}/{n_pages}: '{page.page_title}'",
            )
            db.commit()

            t0 = time_module.monotonic()
            try:
                run_pipeline(db, str(new_task.id), auto_mode=True)
            except Exception as pipeline_err:
                print(f"Pipeline error for task {new_task.id}: {pipeline_err}")
                db.refresh(new_task)
                if new_task.status not in ("failed", "completed"):
                    new_task.status = "failed"
                    new_task.error_log = f"Pipeline exception: {pipeline_err}"
                    db.commit()

            db.refresh(new_task)
            elapsed = time_module.monotonic() - t0

            if new_task.status == "completed":
                db.refresh(new_task)
                cost = float(new_task.total_cost or 0)
                _append_project_log(
                    db,
                    project,
                    f"Page {i + 1}/{n_pages} completed in {_fmt_duration(elapsed)} "
                    f"(cost: ${cost:.4f})",
                )
                db.commit()

            if new_task.status != "completed":
                if new_task.status == "failed":
                    error_detail = new_task.error_log or "Unknown error"
                elif new_task.status == "processing":
                    pause_info = (new_task.step_results or {}).get("_pipeline_pause", {})
                    error_detail = (
                        f"Pipeline stuck in processing. Pause state: {pause_info}"
                    )
                else:
                    error_detail = f"Unexpected task status: {new_task.status}"

                short_err = (error_detail or "")[:200]
                _append_project_log(
                    db,
                    project,
                    f"Page {i + 1}/{n_pages} FAILED: {short_err}. Skipping.",
                    level="error",
                )
                db.commit()

                failed_pages.append(
                    {
                        "page": page.page_title,
                        "keyword": keyword,
                        "task_id": str(new_task.id),
                        "task_status": str(new_task.status),
                        "error": error_detail,
                    }
                )
                print(
                    f"[Project {project_id}] Page skipped (non-completed task): "
                    f"{page.page_title} — {new_task.status}"
                )

                db.refresh(project)
                if project.stopping_requested:
                    project.status = "stopped"
                    project.stopping_requested = False
                    project.completed_at = datetime.utcnow()
                    if failed_pages:
                        project.error_log = json.dumps(failed_pages, ensure_ascii=False)
                    _append_project_log(
                        db, project, "Project stopped by user.", level="warning"
                    )
                    db.commit()
                    print(f"Project {project_id} stopped by user after task {new_task.id}")
                    return

                continue

            db.refresh(project)
            if project.stopping_requested:
                project.status = "stopped"
                project.stopping_requested = False
                project.completed_at = datetime.utcnow()
                if failed_pages:
                    project.error_log = json.dumps(failed_pages, ensure_ascii=False)
                _append_project_log(
                    db, project, "Project stopped by user.", level="warning"
                )
                db.commit()
                print(f"Project {project_id} stopped by user after task {new_task.id}")
                return

        project.current_page_index = len(pages)
        if project.started_at is None:
            project.started_at = datetime.utcnow()
        build_site(db, project_id)

        project.status = "completed"
        if failed_pages:
            project.error_log = json.dumps(failed_pages, ensure_ascii=False)
        else:
            project.error_log = None
        project.completed_at = datetime.utcnow()

        all_tasks = db.query(Task).filter(Task.project_id == project.id).all()
        total_cost = float(sum((t.total_cost or 0) for t in all_tasks))
        ok = sum(1 for t in all_tasks if t.status == "completed")
        fail_n = sum(1 for t in all_tasks if t.status == "failed")
        _append_project_log(
            db,
            project,
            f"Project completed: {ok}/{n_pages} pages successful, {fail_n} failed. "
            f"Total cost: ${total_cost:.4f}",
        )
        db.commit()

    except Exception as exc:
        if project:
            project.status = "failed"
            project.error_log = traceback.format_exc()
            project.completed_at = datetime.utcnow()
            try:
                _append_project_log(
                    db,
                    project,
                    f"Project failed: {exc!s}",
                    level="error",
                )
            except Exception:
                pass
            db.commit()
    finally:
        db.close()


@celery_app.task
def cleanup_stale_tasks():
    """
    Periodic task to clean up jobs stuck in 'processing' state
    and re-queue stale pending projects.
    """
    db = SessionLocal()
    from app.models.task import Task
    from app.models.project import SiteProject
    from datetime import datetime, timedelta
    
    try:
        from sqlalchemy import or_, and_
        # If task has been processing without heartbeat for more than 30 mins
        stale_threshold = datetime.utcnow() - timedelta(minutes=30)
        stale_tasks = db.query(Task).filter(
            Task.status == "processing",
            or_(
                Task.last_heartbeat < stale_threshold,
                and_(Task.last_heartbeat.is_(None), Task.updated_at < stale_threshold)
            )
        ).all()
        
        for t in stale_tasks:
            t.status = "stale"
            t.error_log = "Task timed out and was cleaned up by Celery Beat (Stale state)."
            
        if stale_tasks:
            db.commit()
            print(f"Cleaned up {len(stale_tasks)} stale tasks.")
        
        # Re-queue pending projects older than 10 minutes
        project_cutoff = datetime.utcnow() - timedelta(minutes=10)
        stale_projects = db.query(SiteProject).filter(
            SiteProject.status == "pending",
            SiteProject.created_at < project_cutoff
        ).all()
        
        for proj in stale_projects:
            print(f"Re-queuing stale project {proj.id}")
            process_site_project.delay(str(proj.id))
            
    except Exception as e:
        print(f"Error in cleanup_stale_tasks: {e}")
    finally:
        db.close()
