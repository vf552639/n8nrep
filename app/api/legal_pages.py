from typing import Optional, Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.blueprint import BlueprintPage
from app.models.template import LegalPageTemplate, LEGAL_PAGE_TYPES

router = APIRouter()


class LegalPageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    page_type: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1)
    content_format: str = Field(default="text", pattern="^(text|html)$")
    variables: dict = Field(default_factory=dict)
    notes: Optional[str] = None
    is_active: bool = True


class LegalPageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    page_type: Optional[str] = Field(None, min_length=1, max_length=50)
    content: Optional[str] = None
    content_format: Optional[str] = Field(None, pattern="^(text|html)$")
    variables: Optional[dict] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


def _validate_page_type(pt: str) -> None:
    if pt not in LEGAL_PAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid page_type. Allowed: {list(LEGAL_PAGE_TYPES)}",
        )


@router.get("/meta/page-types")
def page_types() -> dict[str, Any]:
    return {"page_types": list(LEGAL_PAGE_TYPES)}


@router.get("/for-blueprint/{blueprint_id}")
def legal_templates_for_blueprint(blueprint_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    pages = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.blueprint_id == blueprint_id)
        .order_by(BlueprintPage.sort_order)
        .all()
    )
    ordered_types: List[str] = []
    page_type_title: Dict[str, str] = {}
    page_type_defaults: Dict[str, Optional[str]] = {}
    for p in pages:
        if p.page_type in LEGAL_PAGE_TYPES and p.page_type not in page_type_title:
            ordered_types.append(p.page_type)
            page_type_title[p.page_type] = p.page_title
            did = getattr(p, "default_legal_template_id", None)
            page_type_defaults[p.page_type] = str(did) if did else None

    legal_page_types: List[dict[str, Any]] = []
    for pt in ordered_types:
        templates = (
            db.query(LegalPageTemplate)
            .filter(
                LegalPageTemplate.page_type == pt,
                LegalPageTemplate.is_active == True,  # noqa: E712
            )
            .order_by(LegalPageTemplate.name)
            .all()
        )
        legal_page_types.append(
            {
                "page_type": pt,
                "page_title": page_type_title[pt],
                "default_template_id": page_type_defaults.get(pt),
                "templates": [{"id": str(t.id), "name": t.name} for t in templates],
            }
        )
    return {"legal_page_types": legal_page_types}


@router.get("/by-page-type/{page_type}")
def list_by_page_type(page_type: str, db: Session = Depends(get_db)) -> List[dict[str, Any]]:
    _validate_page_type(page_type)
    rows = (
        db.query(LegalPageTemplate)
        .filter(
            LegalPageTemplate.page_type == page_type,
            LegalPageTemplate.is_active == True,  # noqa: E712
        )
        .order_by(LegalPageTemplate.name)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "page_type": r.page_type,
            "content_format": r.content_format or "text",
        }
        for r in rows
    ]


@router.get("/")
def list_legal_pages(
    page_type: Optional[str] = Query(None, description="Filter by page_type"),
    db: Session = Depends(get_db),
) -> List[dict[str, Any]]:
    q = db.query(LegalPageTemplate)
    if page_type and page_type.strip():
        q = q.filter(LegalPageTemplate.page_type == page_type.strip())
    rows = q.order_by(LegalPageTemplate.name, LegalPageTemplate.page_type).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "page_type": r.page_type,
            "content_format": r.content_format or "text",
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.get("/{legal_id}")
def get_legal_page(legal_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    r = db.query(LegalPageTemplate).filter(LegalPageTemplate.id == legal_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": str(r.id),
        "name": r.name,
        "page_type": r.page_type,
        "content": r.content,
        "content_format": r.content_format or "text",
        "variables": r.variables or {},
        "notes": r.notes,
        "is_active": r.is_active,
    }


@router.post("/")
def create_legal_page(body: LegalPageCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    _validate_page_type(body.page_type)
    name = body.name.strip()
    dup = (
        db.query(LegalPageTemplate)
        .filter(
            LegalPageTemplate.name == name,
            LegalPageTemplate.page_type == body.page_type,
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=409, detail="A template with this name and page_type already exists")
    r = LegalPageTemplate(
        name=name,
        page_type=body.page_type,
        content=body.content,
        content_format=body.content_format,
        variables=body.variables or {},
        notes=(body.notes or "").strip() or None,
        is_active=body.is_active,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": str(r.id)}


@router.put("/{legal_id}")
def update_legal_page(legal_id: str, body: LegalPageUpdate, db: Session = Depends(get_db)) -> dict[str, str]:
    r = db.query(LegalPageTemplate).filter(LegalPageTemplate.id == legal_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    if "page_type" in data and data["page_type"]:
        _validate_page_type(data["page_type"])
    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()
    new_name = data.get("name", r.name)
    new_pt = data.get("page_type", r.page_type)
    if (new_name, new_pt) != (r.name, r.page_type):
        dup = (
            db.query(LegalPageTemplate)
            .filter(
                LegalPageTemplate.name == new_name,
                LegalPageTemplate.page_type == new_pt,
                LegalPageTemplate.id != r.id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=409, detail="Duplicate name + page_type")
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return {"id": str(r.id)}


@router.delete("/{legal_id}")
def delete_legal_page(legal_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    r = db.query(LegalPageTemplate).filter(LegalPageTemplate.id == legal_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(r)
    db.commit()
    return {"msg": "Deleted"}
