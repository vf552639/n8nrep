import json
import time as time_module
import traceback
from datetime import datetime, timedelta

import structlog
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.database import SessionLocal
from app.services.pipeline import run_pipeline
from app.workers.celery_app import celery_app


def _append_project_log(db, project, msg: str, level: str = "info") -> None:
    logs = list(project.log_events or [])
    logs.append(
        {
            "ts": datetime.utcnow().isoformat() + "Z",
            "msg": msg,
            "level": level,
        }
    )
    project.log_events = logs[-500:]
    flag_modified(project, "log_events")


def _load_failed_pages(project) -> list:
    if not project.error_log:
        return []
    try:
        data = json.loads(project.error_log)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_failed_page(project, failed_page: dict) -> None:
    failed_pages = _load_failed_pages(project)
    failed_pages.append(failed_page)
    project.error_log = json.dumps(failed_pages, ensure_ascii=False)


def _merge_additional_keywords(existing: str | None, new_list: list[str]) -> str:
    parts: list[str] = []
    seen = set()
    if existing:
        for x in existing.split(","):
            t = x.strip()
            if not t:
                continue
            low = t.lower()
            if low not in seen:
                parts.append(t)
                seen.add(low)
    for k in new_list:
        kl = k.strip()
        if not kl:
            continue
        low = kl.lower()
        if low not in seen:
            parts.append(kl)
            seen.add(low)
    return ", ".join(parts)


def _fmt_duration(seconds: float) -> str:
    s = round(seconds)
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
        structlog.contextvars.bind_contextvars(task_id=str(task_id))
        try:
            run_pipeline(db, task_id)
        finally:
            structlog.contextvars.clear_contextvars()

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


def finalize_project(db, project_id: str):
    from app.models.blueprint import BlueprintPage
    from app.models.project import SiteProject
    from app.models.task import Task
    from app.services.site_builder import build_site

    project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
    if not project:
        return

    pages = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.blueprint_id == project.blueprint_id)
        .order_by(BlueprintPage.sort_order)
        .all()
    )
    n_pages = len(pages)
    project.current_page_index = n_pages
    if project.started_at is None:
        project.started_at = datetime.utcnow()

    build_site(db, project_id)

    all_tasks = db.query(Task).filter(Task.project_id == project.id).all()
    total_cost = float(sum((t.total_cost or 0) for t in all_tasks))
    ok = sum(1 for t in all_tasks if t.status == "completed")
    fail_n = sum(1 for t in all_tasks if t.status == "failed")

    project.status = "completed"
    if not _load_failed_pages(project):
        project.error_log = None
    project.completed_at = datetime.utcnow()
    _append_project_log(
        db,
        project,
        f"Project completed: {ok}/{n_pages} pages successful, {fail_n} failed. Total cost: ${total_cost:.4f}",
    )
    db.commit()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def process_project_page(self, project_id: str, page_index: int):
    db = SessionLocal()
    from app.models.blueprint import BlueprintPage
    from app.models.project import SiteProject
    from app.models.task import Task

    project = None
    try:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if not project:
            print(f"Project {project_id} not found!")
            return

        pages = (
            db.query(BlueprintPage)
            .filter(BlueprintPage.blueprint_id == project.blueprint_id)
            .order_by(BlueprintPage.sort_order)
            .all()
        )
        n_pages = len(pages)
        if page_index < 0 or page_index >= n_pages:
            _append_project_log(db, project, f"Invalid page index {page_index}.", level="error")
            db.commit()
            return

        if project.stopping_requested:
            project.status = "stopped"
            project.stopping_requested = False
            project.completed_at = datetime.utcnow()
            _append_project_log(db, project, "Project stopped by user.", level="warning")
            db.commit()
            return

        page = pages[page_index]
        project.current_page_index = page_index
        if project.started_at is None:
            project.started_at = datetime.utcnow()
        db.commit()

        template = page.keyword_template
        if getattr(project, "seed_is_brand", False) and getattr(page, "keyword_template_brand", None):
            template = page.keyword_template_brand
        keyword = template.replace("{seed}", project.seed_keyword)
        proj_serp = getattr(project, "serp_config", None) or {}

        existing_task = (
            db.query(Task)
            .filter(
                Task.project_id == project.id,
                Task.blueprint_page_id == page.id,
                Task.status.in_(["pending", "failed"]),
            )
            .first()
        )
        if existing_task:
            project_task = existing_task
            project_task.status = "pending"
            project_task.error_log = None
            project_task.serp_config = proj_serp
            db.commit()
        else:
            project_task = Task(
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
            db.add(project_task)
            db.commit()
            db.refresh(project_task)

        db.refresh(project)
        pk_data = getattr(project, "project_keywords", None) or {}
        clustered_data = pk_data.get("clustered") if isinstance(pk_data, dict) else {}
        page_cluster = clustered_data.get(page.page_slug, {}) if isinstance(clustered_data, dict) else {}
        assigned = page_cluster.get("assigned_keywords") if isinstance(page_cluster, dict) else []
        if isinstance(assigned, list) and assigned:
            clustered_kws = [str(x).strip() for x in assigned if str(x).strip()]
            merged = _merge_additional_keywords(project_task.additional_keywords, clustered_kws)
            if merged != (project_task.additional_keywords or ""):
                project_task.additional_keywords = merged
                db.commit()
                db.refresh(project_task)

        _append_project_log(
            db,
            project,
            f"Starting page {page_index + 1}/{n_pages}: '{page.page_title}'",
        )
        db.commit()

        t0 = time_module.monotonic()
        try:
            structlog.contextvars.bind_contextvars(
                task_id=str(project_task.id),
                project_id=str(project.id),
            )
            try:
                run_pipeline(db, str(project_task.id), auto_mode=True)
            finally:
                structlog.contextvars.clear_contextvars()
        except Exception as pipeline_err:
            db.refresh(project_task)
            if project_task.status not in ("failed", "completed"):
                project_task.status = "failed"
                project_task.error_log = f"Pipeline exception: {pipeline_err}"
                db.commit()

        db.refresh(project_task)
        db.refresh(project)
        elapsed = time_module.monotonic() - t0

        if project_task.status == "completed":
            cost = float(project_task.total_cost or 0)
            _append_project_log(
                db,
                project,
                f"Page {page_index + 1}/{n_pages} completed in {_fmt_duration(elapsed)} (cost: ${cost:.4f})",
            )
            project.current_page_index = page_index + 1
            db.commit()
        else:
            if project_task.status == "failed":
                error_detail = project_task.error_log or "Unknown error"
            elif project_task.status == "processing":
                pause_info = (project_task.step_results or {}).get("_pipeline_pause", {})
                error_detail = f"Pipeline stuck in processing. Pause state: {pause_info}"
            else:
                error_detail = f"Unexpected task status: {project_task.status}"

            _append_project_log(
                db,
                project,
                f"Page {page_index + 1}/{n_pages} FAILED: {(error_detail or '')[:200]}. Skipping.",
                level="error",
            )
            _save_failed_page(
                project,
                {
                    "page": page.page_title,
                    "keyword": keyword,
                    "task_id": str(project_task.id),
                    "task_status": str(project_task.status),
                    "error": error_detail,
                },
            )
            project.current_page_index = page_index + 1
            db.commit()

        if project.stopping_requested:
            project.status = "stopped"
            project.stopping_requested = False
            project.completed_at = datetime.utcnow()
            _append_project_log(db, project, "Project stopped by user.", level="warning")
            db.commit()
            return
    except Exception as exc:
        if project:
            project.status = "failed"
            project.error_log = traceback.format_exc()
            project.completed_at = datetime.utcnow()
            _append_project_log(db, project, f"Project failed on page worker: {exc!s}", level="error")
            db.commit()
    finally:
        db.close()

    advance_project.delay(project_id, False)


@celery_app.task(bind=True)
def advance_project(self, project_id: str, approved: bool = False):
    db = SessionLocal()
    from app.models.blueprint import BlueprintPage
    from app.models.project import SiteProject
    from app.models.task import Task

    try:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if not project:
            return

        if project.stopping_requested:
            project.status = "stopped"
            project.stopping_requested = False
            project.completed_at = datetime.utcnow()
            _append_project_log(db, project, "Project stopped by user.", level="warning")
            db.commit()
            return

        pages = (
            db.query(BlueprintPage)
            .filter(BlueprintPage.blueprint_id == project.blueprint_id)
            .order_by(BlueprintPage.sort_order)
            .all()
        )
        done_tasks = (
            db.query(Task)
            .filter(
                Task.project_id == project.id,
                Task.status.in_(["completed", "failed", "stale"]),
            )
            .all()
        )
        done_page_ids = {str(t.blueprint_page_id) for t in done_tasks if t.blueprint_page_id}

        next_page_index = None
        for idx, pg in enumerate(pages):
            if str(pg.id) not in done_page_ids:
                next_page_index = idx
                break

        if next_page_index is None:
            finalize_project(db, project_id)
            return

        if getattr(settings, "PROJECT_PAGE_APPROVAL", False) and not approved:
            last_completed = (
                db.query(Task)
                .filter(Task.project_id == project.id, Task.status == "completed")
                .order_by(Task.updated_at.desc())
                .first()
            )
            if last_completed:
                project.status = "awaiting_page_approval"
                _append_project_log(
                    db,
                    project,
                    f"Page '{last_completed.main_keyword}' completed. Waiting for approval before next page.",
                    level="warning",
                )
                db.commit()
                return

        project.status = "generating"
        db.commit()
        process_project_page.delay(project_id, next_page_index)
    except Exception as exc:
        try:
            project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
            if project:
                project.status = "failed"
                project.error_log = str(exc)
                project.completed_at = datetime.utcnow()
                _append_project_log(db, project, f"Coordinator failed: {exc!s}", level="error")
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def process_site_project(self, project_id: str):
    """
    Starter project task: initialize status and launch coordinator.
    """
    db = SessionLocal()
    from app.models.project import SiteProject

    project = None
    try:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if not project:
            print(f"Project {project_id} not found!")
            return

        project.status = "generating"
        if getattr(project, "generation_started_at", None) is None:
            project.generation_started_at = datetime.utcnow()
        if project.started_at is None:
            project.started_at = datetime.utcnow()
        project.completed_at = None
        _append_project_log(db, project, "Project started. Launching page-by-page generation.")
        db.commit()

        advance_project.delay(project_id, False)
    except Exception as exc:
        if project:
            project.status = "failed"
            project.error_log = str(exc)
            project.completed_at = datetime.utcnow()
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
    from app.models.project import SiteProject
    from app.models.task import Task
    from app.services.pipeline import add_log

    try:
        from sqlalchemy import and_, or_

        now = datetime.utcnow()
        stale_minutes = int(getattr(settings, "STALE_TASK_TIMEOUT_MINUTES", 15))
        stale_threshold = now - timedelta(minutes=stale_minutes)
        step_timeout = timedelta(minutes=int(getattr(settings, "STEP_TIMEOUT_MINUTES", 15)))
        stale_tasks = (
            db.query(Task)
            .filter(
                Task.status == "processing",
                or_(
                    Task.last_heartbeat < stale_threshold,
                    and_(Task.last_heartbeat.is_(None), Task.updated_at < stale_threshold),
                ),
            )
            .all()
        )

        for t in stale_tasks:
            t.status = "stale"
            t.error_log = "Task timed out and was cleaned up by Celery Beat (Stale state)."

        if stale_tasks:
            db.commit()
            print(f"Cleaned up {len(stale_tasks)} stale tasks.")

        processing_tasks = db.query(Task).filter(Task.status == "processing").all()
        step_timed_out = 0
        for task in processing_tasks:
            step_results = task.step_results or {}
            if not isinstance(step_results, dict):
                continue
            for step_name, step_data in step_results.items():
                if step_name.startswith("_") or not isinstance(step_data, dict):
                    continue
                if step_data.get("status") != "running":
                    continue
                started_at_str = step_data.get("started_at")
                if not started_at_str:
                    continue
                try:
                    started_at = datetime.fromisoformat(started_at_str)
                except (TypeError, ValueError):
                    continue
                if now - started_at > step_timeout:
                    step_data["status"] = "failed"
                    step_data["error"] = (
                        f"Step timed out after {int(getattr(settings, 'STEP_TIMEOUT_MINUTES', 15))} minutes"
                    )
                    task.step_results = dict(step_results)
                    task.status = "stale"
                    task.error_log = f"Step '{step_name}' timed out after {int(getattr(settings, 'STEP_TIMEOUT_MINUTES', 15))}min"
                    add_log(
                        db,
                        task,
                        f"Step '{step_name}' timed out ({int(getattr(settings, 'STEP_TIMEOUT_MINUTES', 15))}min). Task marked stale.",
                        level="error",
                        step=step_name,
                    )
                    step_timed_out += 1
                    break
        if step_timed_out:
            db.commit()
            print(f"Marked {step_timed_out} tasks stale by step timeout.")

        # Re-queue pending projects older than 10 minutes
        project_cutoff = datetime.utcnow() - timedelta(minutes=10)
        stale_projects = (
            db.query(SiteProject)
            .filter(SiteProject.status == "pending", SiteProject.created_at < project_cutoff)
            .all()
        )

        for proj in stale_projects:
            print(f"Re-queuing stale project {proj.id}")
            process_site_project.delay(str(proj.id))

    except Exception as e:
        print(f"Error in cleanup_stale_tasks: {e}")
    finally:
        db.close()
