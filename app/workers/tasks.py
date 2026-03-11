from celery.exceptions import SoftTimeLimitExceeded, MaxRetriesExceededError
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.services.pipeline import run_pipeline

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
    
    try:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if not project:
            print(f"Project {project_id} not found!")
            return
            
        project.status = "generating"
        db.commit()
        
        pages = db.query(BlueprintPage).filter(BlueprintPage.blueprint_id == project.blueprint_id).order_by(BlueprintPage.sort_order).all()
        
        # Skip already completed pages (enables resume after stop)
        existing_tasks = db.query(Task).filter(
            Task.project_id == project.id,
            Task.status == "completed"
        ).all()
        completed_page_ids = {str(t.blueprint_page_id) for t in existing_tasks}
        
        for i, page in enumerate(pages):
            if str(page.id) in completed_page_ids:
                print(f"Skipping already completed page: {page.page_title}")
                continue
            
            project.current_page_index = i
            db.commit()
            
            # Generate Keyword based on brand fallback vs standard template
            template = page.keyword_template
            if getattr(project, 'seed_is_brand', False) and getattr(page, 'keyword_template_brand', None):
                template = page.keyword_template_brand
            keyword = template.replace("{seed}", project.seed_keyword)
            
            # Check if a pending/failed task already exists for this page (from prior attempt)
            existing_task = db.query(Task).filter(
                Task.project_id == project.id,
                Task.blueprint_page_id == page.id,
                Task.status.in_(["pending", "failed"])
            ).first()
            
            if existing_task:
                new_task = existing_task
                new_task.status = "pending"
                new_task.error_log = None
                db.commit()
            else:
                # Create Task
                new_task = Task(
                    main_keyword=keyword,
                    country=project.country,
                    language=project.language,
                    page_type=page.page_type,
                    target_site_id=project.site_id,
                    author_id=project.author_id,
                    project_id=project.id,
                    blueprint_page_id=page.id,
                    status="pending"
                )
                db.add(new_task)
                db.commit()
                db.refresh(new_task)
            
            # Run pipeline SYNCHRONOUSLY
            try:
                run_pipeline(db, str(new_task.id))
            except Exception as pipeline_err:
                print(f"Pipeline error for task {new_task.id}: {pipeline_err}")
                
            db.refresh(new_task)
            if new_task.status == "failed":
                project.status = "failed"
                project.error_log = f"Failed at page: {page.page_title} - {new_task.error_log}"
                db.commit()
                return
            
            # Cooperative cancellation: check if user requested stop
            db.refresh(project)
            if project.stopping_requested:
                project.status = "stopped"
                project.stopping_requested = False
                db.commit()
                print(f"Project {project_id} stopped by user after task {new_task.id}")
                return

        # If we reached here, everything succeeded
        project.current_page_index = len(pages)
        build_site(db, project_id)
        
        project.status = "completed"
        db.commit()
        
    except Exception as exc:
        if project:
            project.status = "failed"
            project.error_log = traceback.format_exc()
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
