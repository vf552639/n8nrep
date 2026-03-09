from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import func
from typing import List, Optional
from pydantic import BaseModel
import uuid
import os

from app.database import get_db
from app.models.project import SiteProject
from app.models.blueprint import SiteBlueprint
from app.models.site import Site
from app.models.author import Author
from app.models.task import Task

# Imported to defer circular dep issues, will verify app.workers.tasks is available
from app.workers.tasks import process_site_project

router = APIRouter()

class SiteProjectCreate(BaseModel):
    name: str
    blueprint_id: str
    seed_keyword: str
    target_site: str # Domain or name
    country: str
    language: str
    author_id: Optional[int] = None

class SiteProjectResponse(BaseModel):
    id: str
    name: str
    blueprint_id: str
    site_id: str
    seed_keyword: str
    status: str
    current_page_index: int
    build_zip_url: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True

@router.get("/")
def get_projects(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    projects = db.query(SiteProject).order_by(desc(SiteProject.created_at)).offset(skip).limit(limit).all()
    return [{
        "id": str(p.id),
        "name": p.name,
        "blueprint_id": str(p.blueprint_id),
        "site_id": str(p.site_id),
        "seed_keyword": p.seed_keyword,
        "status": p.status,
        "current_page_index": p.current_page_index,
        "build_zip_url": p.build_zip_url,
        "created_at": p.created_at.isoformat()
    } for p in projects]

@router.post("/")
def create_project(project_in: SiteProjectCreate, db: Session = Depends(get_db)):
    # Verify blueprint
    blueprint = db.query(SiteBlueprint).filter(SiteBlueprint.id == project_in.blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
        
    # Verify/create site (similar to tasks.py)
    site = None
    try:
        uuid_obj = uuid.UUID(project_in.target_site, version=4)
        site = db.query(Site).filter(Site.id == str(uuid_obj)).first()
    except ValueError:
        pass
        
    if not site:
        site = db.query(Site).filter(
            (func.lower(Site.domain) == func.lower(project_in.target_site)) | 
            (func.lower(Site.name) == func.lower(project_in.target_site))
        ).first()
        
    if not site:
        site = Site(
            name=project_in.target_site,
            domain=project_in.target_site,
            country=project_in.country,
            language=project_in.language,
            is_active=True
        )
        db.add(site)
        db.commit()
        db.refresh(site)

    # Auto-assign author
    final_author_id = project_in.author_id
    if not final_author_id:
        author = db.query(Author).filter(
            func.lower(Author.country) == project_in.country.lower(),
            func.lower(Author.language) == project_in.language.lower()
        ).first()
        if author:
            final_author_id = author.id

    new_project = SiteProject(
        name=project_in.name,
        blueprint_id=blueprint.id,
        site_id=site.id,
        seed_keyword=project_in.seed_keyword,
        country=project_in.country,
        language=project_in.language,
        author_id=final_author_id,
        status='pending'
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    # Start celery project workflow
    process_site_project.delay(str(new_project.id))
    
    return {"id": str(new_project.id), "status": "Project created and queued"}

@router.get("/{id}")
def get_project_details(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Get all tasks for this project
    tasks = db.query(Task).filter(Task.project_id == id).order_by(Task.created_at).all()
    
    return {
        "id": str(project.id),
        "name": project.name,
        "blueprint_id": str(project.blueprint_id),
        "site_id": str(project.site_id),
        "seed_keyword": project.seed_keyword,
        "status": project.status,
        "current_page_index": project.current_page_index,
        "build_zip_url": project.build_zip_url,
        "created_at": project.created_at.isoformat(),
        "tasks": [{
            "id": str(t.id),
            "blueprint_page_id": str(t.blueprint_page_id) if t.blueprint_page_id else None,
            "status": t.status,
            "main_keyword": t.main_keyword,
            "page_type": t.page_type
        } for t in tasks]
    }

@router.get("/{id}/download")
def download_project_zip(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if not project.build_zip_url or not os.path.exists(project.build_zip_url):
        raise HTTPException(status_code=404, detail="ZIP file not found or not built yet")
        
    return FileResponse(project.build_zip_url, media_type="application/zip", filename=os.path.basename(project.build_zip_url))
