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
        
        for i, page in enumerate(pages):
            project.current_page_index = i
            db.commit()
            
            # Construct keyword
            keyword = page.keyword_template.replace("{seed}", project.seed_keyword)
            
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
    Periodic task to clean up jobs stuck in 'processing' state.
    """
    db = SessionLocal()
    from app.models.task import Task
    from datetime import datetime, timedelta
    
    try:
        # If task has been processing for more than 2 hours, assume it died
        stale_threshold = datetime.utcnow() - timedelta(hours=2)
        stale_tasks = db.query(Task).filter(Task.status == "processing", Task.updated_at < stale_threshold).all()
        
        for t in stale_tasks:
            t.status = "failed"
            t.error_log = "Task timed out and was cleaned up by Celery Beat."
            
        if stale_tasks:
            db.commit()
            print(f"Cleaned up {len(stale_tasks)} stale tasks.")
            
    except Exception as e:
        print(f"Error in cleanup_stale_tasks: {e}")
    finally:
        db.close()

