import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.blueprint import SiteBlueprint, BlueprintPage
from app.models.template import LegalPageTemplate, LEGAL_PAGE_TYPES
from app.services.pipeline_presets import (
    VALID_PRESETS,
    pipeline_steps_use_serp,
    resolve_steps_from_payload,
)

router = APIRouter()


class SiteBlueprintCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool = True


class BlueprintPageCreate(BaseModel):
    page_slug: str
    page_title: str
    page_type: str = "article"
    keyword_template: str
    keyword_template_brand: Optional[str] = None
    filename: str
    sort_order: int = 0
    nav_label: Optional[str] = None
    show_in_nav: bool = True
    show_in_footer: bool = True
    use_serp: bool = True
    pipeline_preset: str = "full"
    pipeline_steps_custom: Optional[List[str]] = None
    default_legal_template_id: Optional[str] = None

    @field_validator("pipeline_preset")
    @classmethod
    def validate_pipeline_preset(cls, v: str) -> str:
        s = (v or "full").strip().lower()
        if s not in VALID_PRESETS:
            raise ValueError(
                f"pipeline_preset must be one of {sorted(VALID_PRESETS)}, got {v!r}"
            )
        return s


def _validate_default_legal_template(
    db: Session,
    page_type: str,
    default_legal_template_id: Optional[str],
) -> Optional[str]:
    """Validate and return normalized template_id or None."""
    if not default_legal_template_id or not str(default_legal_template_id).strip():
        return None
    if page_type not in LEGAL_PAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="default_legal_template_id can only be set for legal page types: "
            f"{list(LEGAL_PAGE_TYPES)}",
        )
    try:
        tid = uuid.UUID(str(default_legal_template_id).strip())
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid default_legal_template_id: {default_legal_template_id}",
        ) from e
    tpl = (
        db.query(LegalPageTemplate)
        .filter(
            LegalPageTemplate.id == tid,
            LegalPageTemplate.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not tpl:
        raise HTTPException(
            status_code=400,
            detail=f"Legal template not found or inactive: {default_legal_template_id}",
        )
    if tpl.page_type != page_type:
        raise HTTPException(
            status_code=400,
            detail=f"Template page_type '{tpl.page_type}' doesn't match "
            f"blueprint page_type '{page_type}'",
        )
    return str(tpl.id)


def _page_create_dict(page_in: BlueprintPageCreate, db: Session) -> dict:
    payload = page_in.model_dump()
    page_type = (payload.get("page_type") or "article").strip()
    raw_default = payload.pop("default_legal_template_id", None)

    if raw_default and str(raw_default).strip() and page_type not in LEGAL_PAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="default_legal_template_id can only be set for legal page types: "
            f"{list(LEGAL_PAGE_TYPES)}",
        )

    if page_type not in LEGAL_PAGE_TYPES:
        payload["default_legal_template_id"] = None
    else:
        norm = _validate_default_legal_template(db, page_type, raw_default)
        payload["default_legal_template_id"] = uuid.UUID(norm) if norm else None

    payload["page_type"] = page_type
    steps = resolve_steps_from_payload(
        payload.get("pipeline_preset", "full"),
        payload.get("pipeline_steps_custom"),
    )
    payload["use_serp"] = pipeline_steps_use_serp(steps)
    return payload


@router.get("/")
def get_blueprints(db: Session = Depends(get_db)):
    blueprints = db.query(SiteBlueprint).all()
    return [
        {
            "id": str(b.id),
            "name": b.name,
            "slug": b.slug,
            "description": b.description,
            "is_active": b.is_active,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in blueprints
    ]


@router.post("/")
def create_blueprint(blueprint_in: SiteBlueprintCreate, db: Session = Depends(get_db)):
    db_blueprint = SiteBlueprint(**blueprint_in.model_dump())
    db.add(db_blueprint)
    try:
        db.commit()
        db.refresh(db_blueprint)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": str(db_blueprint.id),
        "name": db_blueprint.name,
        "slug": db_blueprint.slug,
    }


@router.get("/{id}/pages")
def get_blueprint_pages(id: str, db: Session = Depends(get_db)):
    pages = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.blueprint_id == id)
        .order_by(BlueprintPage.sort_order)
        .all()
    )
    return [
        {
            "id": str(p.id),
            "blueprint_id": str(p.blueprint_id),
            "page_slug": p.page_slug,
            "page_title": p.page_title,
            "page_type": p.page_type,
            "keyword_template": p.keyword_template,
            "keyword_template_brand": getattr(p, "keyword_template_brand", None),
            "filename": p.filename,
            "sort_order": p.sort_order,
            "nav_label": p.nav_label,
            "show_in_nav": p.show_in_nav,
            "show_in_footer": p.show_in_footer,
            "use_serp": p.use_serp,
            "pipeline_preset": getattr(p, "pipeline_preset", "full") or "full",
            "pipeline_steps_custom": getattr(p, "pipeline_steps_custom", None),
            "default_legal_template_id": (
                str(p.default_legal_template_id) if getattr(p, "default_legal_template_id", None) else None
            ),
        }
        for p in pages
    ]


@router.post("/{id}/pages")
def create_blueprint_page(id: str, page_in: BlueprintPageCreate, db: Session = Depends(get_db)):
    payload = _page_create_dict(page_in, db)
    db_page = BlueprintPage(blueprint_id=id, **payload)
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return {
        "id": str(db_page.id),
        "blueprint_id": str(db_page.blueprint_id),
        "page_slug": db_page.page_slug,
        "page_title": db_page.page_title,
        "sort_order": db_page.sort_order,
    }


@router.put("/{id}/pages/{page_id}")
def update_blueprint_page(id: str, page_id: str, page_in: BlueprintPageCreate, db: Session = Depends(get_db)):
    db_page = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.id == page_id, BlueprintPage.blueprint_id == id)
        .first()
    )
    if not db_page:
        raise HTTPException(status_code=404, detail="Page not found")

    payload = _page_create_dict(page_in, db)
    for key, value in payload.items():
        setattr(db_page, key, value)

    db.commit()
    db.refresh(db_page)
    return {
        "id": str(db_page.id),
        "page_slug": db_page.page_slug,
        "msg": "Updated",
    }


@router.delete("/{id}/pages/{page_id}")
def delete_blueprint_page(id: str, page_id: str, db: Session = Depends(get_db)):
    db_page = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.id == page_id, BlueprintPage.blueprint_id == id)
        .first()
    )
    if not db_page:
        raise HTTPException(status_code=404, detail="Page not found")

    db.delete(db_page)
    db.commit()
    return {"status": "deleted"}
