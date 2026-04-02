from typing import Optional, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.template import LegalPageTemplate, LEGAL_PAGE_TYPES

router = APIRouter()


class LegalPageCreate(BaseModel):
    country: str = Field(..., min_length=2, max_length=10)
    page_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=300)
    html_content: str = Field(..., min_length=1)
    variables: dict = Field(default_factory=dict)
    notes: Optional[str] = None
    is_active: bool = True


class LegalPageUpdate(BaseModel):
    country: Optional[str] = Field(None, min_length=2, max_length=10)
    page_type: Optional[str] = Field(None, min_length=1, max_length=50)
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    html_content: Optional[str] = None
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


@router.get("/")
def list_legal_pages(
    country: Optional[str] = Query(None, description="Filter by country code"),
    db: Session = Depends(get_db),
) -> List[dict[str, Any]]:
    q = db.query(LegalPageTemplate)
    if country:
        q = q.filter(LegalPageTemplate.country == country.strip().upper())
    rows = q.order_by(LegalPageTemplate.country, LegalPageTemplate.page_type).all()
    return [
        {
            "id": str(r.id),
            "country": r.country,
            "page_type": r.page_type,
            "title": r.title,
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
        "country": r.country,
        "page_type": r.page_type,
        "title": r.title,
        "html_content": r.html_content,
        "variables": r.variables or {},
        "notes": r.notes,
        "is_active": r.is_active,
    }


@router.post("/")
def create_legal_page(body: LegalPageCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    _validate_page_type(body.page_type)
    country = body.country.strip().upper()
    dup = (
        db.query(LegalPageTemplate)
        .filter(
            LegalPageTemplate.country == country,
            LegalPageTemplate.page_type == body.page_type,
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=409, detail="A template for this country and page_type already exists")
    r = LegalPageTemplate(
        country=country,
        page_type=body.page_type,
        title=body.title.strip(),
        html_content=body.html_content,
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
    if "country" in data and data["country"]:
        data["country"] = data["country"].strip().upper()
    new_country = data.get("country", r.country)
    new_pt = data.get("page_type", r.page_type)
    if (new_country, new_pt) != (r.country, r.page_type):
        dup = (
            db.query(LegalPageTemplate)
            .filter(
                LegalPageTemplate.country == new_country,
                LegalPageTemplate.page_type == new_pt,
                LegalPageTemplate.id != r.id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=409, detail="Duplicate country + page_type")
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
