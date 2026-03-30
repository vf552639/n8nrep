from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models.site import Site, SiteTemplate
from app.models.task import Task
from app.models.project import SiteProject

router = APIRouter()

class SiteCreate(BaseModel):
    name: str
    domain: str
    country: str
    language: str
    is_active: bool = True

class TemplateCreate(BaseModel):
    template_name: str
    html_template: str
    pages_config: Optional[dict] = None
    is_active: bool = True


class TemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    html_template: Optional[str] = None
    pages_config: Optional[dict] = None
    is_active: Optional[bool] = None

@router.get("/")
def get_sites(db: Session = Depends(get_db)):
    sites = db.query(Site).all()
    return [{"id": str(s.id), "name": s.name, "domain": s.domain, "country": s.country, 
             "language": s.language, "is_active": s.is_active} for s in sites]

@router.post("/")
def create_site(site_in: SiteCreate, db: Session = Depends(get_db)):
    new_site = Site(**site_in.model_dump())
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    return {"id": str(new_site.id)}

@router.delete("/{site_id}")
def delete_site(site_id: str, db: Session = Depends(get_db)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    task_count = db.query(Task).filter(Task.target_site_id == site_id).count()
    project_count = db.query(SiteProject).filter(SiteProject.site_id == site_id).count()

    if task_count > 0 or project_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: site has {task_count} tasks and {project_count} projects. Delete them first.",
        )

    db.query(SiteTemplate).filter(SiteTemplate.site_id == site_id).delete()
    db.delete(site)
    db.commit()
    return {"msg": "Site deleted"}

# --- Templates --- #

@router.get("/{site_id}/templates")
def get_site_templates(site_id: str, db: Session = Depends(get_db)):
    templates = db.query(SiteTemplate).filter(SiteTemplate.site_id == site_id).all()
    return [{
        "id": str(t.id),
        "template_name": t.template_name,
        "usage_count": t.usage_count or 0,
        "is_active": t.is_active,
    } for t in templates]

@router.get("/{site_id}/templates/{template_id}")
def get_template(site_id: str, template_id: str, db: Session = Depends(get_db)):
    template = db.query(SiteTemplate).filter(SiteTemplate.id == template_id).first()
    if not template or str(template.site_id) != site_id:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": str(template.id),
        "template_name": template.template_name,
        "html_template": template.html_template,
        "pages_config": template.pages_config or {},
        "usage_count": template.usage_count or 0,
        "is_active": template.is_active,
    }

@router.post("/{site_id}/templates")
def add_template(site_id: str, t_in: TemplateCreate, db: Session = Depends(get_db)):
    new_template = SiteTemplate(
        site_id=site_id,
        template_name=t_in.template_name,
        html_template=t_in.html_template,
        pages_config=t_in.pages_config,
        is_active=t_in.is_active
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return {"id": str(new_template.id)}


@router.put("/{site_id}/templates/{template_id}")
def update_template(site_id: str, template_id: str, body: TemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(SiteTemplate).filter(SiteTemplate.id == template_id).first()
    if not template or str(template.site_id) != site_id:
        raise HTTPException(status_code=404, detail="Template not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(template, k, v)
    db.commit()
    db.refresh(template)
    return {"id": str(template.id)}


@router.delete("/{site_id}/templates/{template_id}")
def delete_template(site_id: str, template_id: str, db: Session = Depends(get_db)):
    template = db.query(SiteTemplate).filter(SiteTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"msg": "Template deleted"}
