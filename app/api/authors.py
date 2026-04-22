from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.author import Author
from app.models.task import Task
from app.schemas.author import AuthorCreate

router = APIRouter()


def _format_year(val) -> str:
    if val is None or val == "":
        return ""
    s = str(val).strip()
    try:
        num = float(s)
        if num == int(num):
            return str(int(num))
        return s
    except (ValueError, TypeError):
        return s


@router.get("/")
def get_authors(db: Session = Depends(get_db)):
    authors = db.query(Author).all()
    usage_rows = (
        db.query(Author.id, func.count(Task.id))
        .outerjoin(Task, Task.author_id == Author.id)
        .group_by(Author.id)
        .all()
    )
    usage_counts = {int(row[0]): int(row[1]) for row in usage_rows}
    return [
        {
            "id": str(a.id),
            "name": a.author,
            "author": a.author,
            "country": a.country,
            "country_full": a.country_full,
            "language": a.language,
            "co_short": a.co_short,
            "city": a.city,
            "bio": a.bio,
            "imitation": a.imitation,
            "year": _format_year(a.year),
            "face": a.face,
            "target_audience": a.target_audience,
            "rhythms_style": a.rhythms_style,
            "exclude_words": a.exclude_words,
            "usage_count": usage_counts.get(int(a.id), 0),
        }
        for a in authors
    ]


@router.post("/")
def create_author(author_in: AuthorCreate, db: Session = Depends(get_db)):
    new_author = Author(**author_in.model_dump())
    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    return {"id": str(new_author.id)}


@router.put("/{author_id}")
def update_author(author_id: str, data: AuthorCreate, db: Session = Depends(get_db)):
    try:
        aid = int(author_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Author not found") from None
    author = db.query(Author).filter(Author.id == aid).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    for field, value in data.model_dump().items():
        setattr(author, field, value)
    author.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(author)
    return {"id": str(author.id), "author": author.author, "status": "updated"}


@router.delete("/{author_id}")
def delete_author(author_id: str, db: Session = Depends(get_db)):
    try:
        aid = int(author_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Author not found") from None
    author = db.query(Author).filter(Author.id == aid).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    db.delete(author)
    db.commit()
    return {"msg": "Author deleted"}
