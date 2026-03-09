from typing import List, Optional
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import func
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models.task import Task
from app.models.site import Site
from app.models.author import Author
from app.workers.tasks import process_generation_task

router = APIRouter()

class TaskCreate(BaseModel):
    main_keyword: str
    country: str
    language: str
    target_site: str
    author_id: Optional[int] = None
    additional_keywords: Optional[str] = None
    priority: int = 0
    page_type: str = 'article'

class TaskResponse(BaseModel):
    id: str
    main_keyword: str
    status: str
    created_at: str

    class Config:
        from_attributes = True

@router.get("/")
def get_tasks(skip: int = 0, limit: int = 50, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.order_by(desc(Task.created_at)).offset(skip).limit(limit).all()
    
    # Quick formatting
    return [{
        "id": str(t.id),
        "main_keyword": t.main_keyword,
        "country": t.country,
        "language": t.language,
        "page_type": t.page_type,
        "status": t.status,
        "target_site_id": str(t.target_site_id),
        "created_at": t.created_at.isoformat(),
        "error_log": t.error_log
    } for t in tasks]

@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {
        "id": str(task.id),
        "main_keyword": task.main_keyword,
        "status": task.status,
        "page_type": task.page_type,
        "outline": task.outline,
        "serp_data": task.serp_data,
        "error_log": task.error_log,
        "created_at": task.created_at.isoformat(),
        "logs": task.logs or []
    }

def calculate_progress(step_results: dict) -> int:
    """Returns progress percentage 0-100 based on 14 steps"""
    total_steps = 14
    completed = sum(1 for v in (step_results or {}).values() if v.get("status") == "completed")
    return int((completed / total_steps) * 100)

@router.get("/{task_id}/steps")
def get_task_steps(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": str(task.id),
        "status": task.status,
        "progress": calculate_progress(task.step_results),
        "step_results": task.step_results or {},
        "current_step": next((k for k, v in (task.step_results or {}).items() if v.get("status") == "running"), None)
    }

@router.post("/")
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    # Verify or create site
    site = None
    try:
        # Check if it's a valid UUID first
        uuid_obj = uuid.UUID(task_in.target_site, version=4)
        site = db.query(Site).filter(Site.id == str(uuid_obj)).first()
    except ValueError:
        pass
        
    if not site:
        site = db.query(Site).filter(
            (func.lower(Site.domain) == func.lower(task_in.target_site)) | 
            (func.lower(Site.name) == func.lower(task_in.target_site))
        ).first()
        
    if not site:
        # Automatically create the site if it wasn't found
        site = Site(
            name=task_in.target_site,
            domain=task_in.target_site,
            country=task_in.country,
            language=task_in.language,
            is_active=True
        )
        db.add(site)
        db.commit()
        db.refresh(site)

    # Auto-assign author if not provided
    final_author_id = task_in.author_id
    if not final_author_id:
        author = db.query(Author).filter(
            func.lower(Author.country) == task_in.country.lower(),
            func.lower(Author.language) == task_in.language.lower()
        ).first()
        if author:
            final_author_id = author.id

    new_task = Task(
        main_keyword=task_in.main_keyword,
        country=task_in.country,
        language=task_in.language,
        page_type=task_in.page_type,
        target_site_id=site.id,
        author_id=final_author_id,
        additional_keywords=task_in.additional_keywords,
        priority=task_in.priority
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Dispatch Celery task
    process_generation_task.delay(str(new_task.id))
    
    return {"id": str(new_task.id), "status": "Task created and queued"}

@router.post("/bulk")
async def create_tasks_bulk(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    CSV must have columns: keyword, country, language, site_name
    """
    contents = await file.read()
    reader = csv.DictReader(io.StringIO(contents.decode('utf-8')))
    
    tasks_created = 0
    errors = []
    
    for row in reader:
        try:
            site_name = row.get("site_name")
            site = db.query(Site).filter(func.lower(Site.name) == func.lower(site_name)).first()
            if not site:
                errors.append(f"Site {site_name} not found for keyword {row['keyword']}")
                continue
                
            new_task = Task(
                main_keyword=row["keyword"],
                country=row["country"],
                language=row["language"],
                page_type=row.get("page_type", "article"),
                target_site_id=site.id
            )
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
            
            process_generation_task.delay(str(new_task.id))
            tasks_created += 1
        except Exception as e:
            errors.append(f"Error processing row {row}: {e}")
            db.rollback()
            
    return {"tasks_created": tasks_created, "errors": errors}

@router.post("/{task_id}/retry")
def retry_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "failed":
        raise HTTPException(status_code=400, detail="Can only retry failed tasks")
        
    task.status = "pending"
    task.error_log = None
    task.retry_count += 1
    db.commit()
    
    process_generation_task.delay(str(task.id))
    return {"msg": "Task queued for retry"}

@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    db.delete(task)
    db.commit()
    return {"msg": "Task deleted"}
