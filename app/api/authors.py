import time
from datetime import datetime
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.author import Author
from app.models.task import Task
from app.schemas.author import AuthorCreate

router = APIRouter()

_CACHE_LOCK = Lock()
_AUTHORS_LIST_CACHE: dict[tuple[bool, int, int], tuple[float, list]] = {}
_CACHE_TTL_SEC = 60.0


def _authors_cache_clear() -> None:
    with _CACHE_LOCK:
        _AUTHORS_LIST_CACHE.clear()


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


def _usage_counts_for_ids(db: Session, author_ids: list[int]) -> dict[int, int]:
    if not author_ids:
        return {}
    usage_rows = (
        db.query(Author.id, func.count(Task.id))
        .outerjoin(Task, Task.author_id == Author.id)
        .filter(Author.id.in_(author_ids))
        .group_by(Author.id)
        .all()
    )
    return {int(row[0]): int(row[1]) for row in usage_rows}


def _author_row_to_full_dict(a: Author, usage_counts: dict[int, int]) -> dict:
    aid = int(a.id)
    return {
        "id": str(aid),
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
        "usage_count": usage_counts.get(aid, 0),
    }


def _author_light_tuple_to_dict(row, usage_counts: dict[int, int]) -> dict:
    aid = int(row.id)
    return {
        "id": str(aid),
        "name": row.author,
        "author": row.author,
        "country": row.country,
        "country_full": row.country_full,
        "language": row.language,
        "year": _format_year(row.year),
        "usage_count": usage_counts.get(aid, 0),
    }


def _build_authors_list(
    db: Session,
    *,
    full: bool,
    limit: int,
    offset: int,
) -> list:
    if full:
        authors = db.query(Author).order_by(Author.id).offset(offset).limit(limit).all()
        ids = [int(a.id) for a in authors]
        usage_counts = _usage_counts_for_ids(db, ids)
        return [_author_row_to_full_dict(a, usage_counts) for a in authors]

    rows = (
        db.query(
            Author.id,
            Author.author,
            Author.country,
            Author.country_full,
            Author.language,
            Author.year,
        )
        .order_by(Author.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    ids = [int(r.id) for r in rows]
    usage_counts = _usage_counts_for_ids(db, ids)
    return [_author_light_tuple_to_dict(r, usage_counts) for r in rows]


@router.get("/")
def get_authors(
    db: Session = Depends(get_db),
    full: bool = Query(False, description="Include heavy Text columns (bio, imitation, …)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    cache_key = (full, limit, offset)
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _AUTHORS_LIST_CACHE.get(cache_key)
        if hit is not None:
            cached_at, payload = hit
            if now - cached_at <= _CACHE_TTL_SEC:
                return payload
            del _AUTHORS_LIST_CACHE[cache_key]

    payload = _build_authors_list(db, full=full, limit=limit, offset=offset)

    with _CACHE_LOCK:
        _AUTHORS_LIST_CACHE[cache_key] = (now, payload)

    return payload


@router.post("/")
def create_author(author_in: AuthorCreate, db: Session = Depends(get_db)):
    new_author = Author(**author_in.model_dump())
    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    _authors_cache_clear()
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
    _authors_cache_clear()
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
    _authors_cache_clear()
    return {"msg": "Author deleted"}
