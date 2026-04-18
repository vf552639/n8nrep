from typing import Optional, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.site import Site
from app.models.task import Task
from app.models.project import SiteProject
from app.models.template import Template
from app.utils.language_normalize import normalize_language

router = APIRouter()


class SiteCreate(BaseModel):
    name: str
    domain: str
    country: str
    language: str
    is_active: bool = True
    template_id: Optional[str] = None
    legal_info: Optional[dict] = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
        return v

    @field_validator("language")
    @classmethod
    def normalize_language_create(cls, v: str) -> str:
        out = normalize_language(v) or ""
        if not out:
            raise ValueError("Language is required")
        return out


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    template_id: Optional[str] = None
    legal_info: Optional[dict] = None

    @field_validator("country")
    @classmethod
    def validate_country_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
        return v

    @field_validator("language")
    @classmethod
    def normalize_language_update(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        out = normalize_language(v)
        return out if out else None


def _site_out(s: Site, db: Session) -> dict[str, Any]:
    tpl_name = None
    if s.template_id:
        t = db.query(Template).filter(Template.id == s.template_id).first()
        if t:
            tpl_name = t.name
    return {
        "id": str(s.id),
        "name": s.name,
        "domain": s.domain,
        "country": s.country,
        "language": s.language,
        "is_active": s.is_active,
        "template_id": str(s.template_id) if s.template_id else None,
        "template_name": tpl_name,
        "has_template": bool(s.template_id),
        "legal_info": s.legal_info if isinstance(s.legal_info, dict) else {},
    }


@router.get("/")
def get_sites(db: Session = Depends(get_db)) -> List[dict[str, Any]]:
    sites = db.query(Site).order_by(Site.name).all()
    return [_site_out(s, db) for s in sites]


@router.get("/{site_id}")
def get_site(site_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return _site_out(site, db)


@router.post("/")
def create_site(site_in: SiteCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    data = site_in.model_dump()
    tid = data.pop("template_id", None)
    if tid == "":
        tid = None
    if tid:
        if not db.query(Template).filter(Template.id == tid).first():
            raise HTTPException(status_code=400, detail="template_id not found")
    new_site = Site(**data, template_id=tid)
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    return {"id": str(new_site.id)}


@router.patch("/{site_id}")
def update_site(site_id: str, body: SiteUpdate, db: Session = Depends(get_db)) -> dict[str, str]:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    data = body.model_dump(exclude_unset=True)
    if "template_id" in data:
        tid = data["template_id"]
        if tid is None or tid == "":
            site.template_id = None
        else:
            if not db.query(Template).filter(Template.id == tid).first():
                raise HTTPException(status_code=400, detail="template_id not found")
            site.template_id = tid
        del data["template_id"]
    for k, v in data.items():
        setattr(site, k, v)
    db.commit()
    db.refresh(site)
    return {"id": str(site.id)}


@router.delete("/{site_id}")
def delete_site(site_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
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

    db.delete(site)
    db.commit()
    return {"msg": "Site deleted"}
