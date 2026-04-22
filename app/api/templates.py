from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.site import Site
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate

router = APIRouter()


def _sites_count(db: Session, template_id: UUID) -> int:
    return db.query(func.count(Site.id)).filter(Site.template_id == template_id).scalar() or 0


@router.get("/")
def list_templates(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(Template).order_by(Template.name).all()
    out: list[dict[str, Any]] = []
    for t in rows:
        out.append(
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "preview_screenshot": t.preview_screenshot,
                "is_active": t.is_active,
                "sites_count": _sites_count(db, t.id),
            }
        )
    return out


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    t = db.query(Template).filter(Template.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": str(t.id),
        "name": t.name,
        "html_template": t.html_template,
        "description": t.description,
        "preview_screenshot": t.preview_screenshot,
        "is_active": t.is_active,
        "sites_count": _sites_count(db, t.id),
    }


@router.post("/")
def create_template(body: TemplateCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    t = Template(
        name=body.name.strip(),
        html_template=body.html_template,
        description=(body.description or "").strip() or None,
        preview_screenshot=body.preview_screenshot,
        is_active=body.is_active,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": str(t.id)}


@router.put("/{template_id}")
def update_template(template_id: str, body: TemplateUpdate, db: Session = Depends(get_db)) -> dict[str, str]:
    t = db.query(Template).filter(Template.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "name" and isinstance(v, str):
            v = v.strip()
        if k == "description" and isinstance(v, str):
            v = v.strip() or None
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return {"id": str(t.id)}


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    t = db.query(Template).filter(Template.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    n = _sites_count(db, t.id)
    if n > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Template is used by {n} site(s). Remove or reassign sites first.",
        )
    db.delete(t)
    db.commit()
    return {"msg": "Template deleted"}
