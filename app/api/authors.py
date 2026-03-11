from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.author import Author

router = APIRouter()

class AuthorCreate(BaseModel):
    author: str
    country: str
    language: str
    bio: str = None
    co_short: str = None
    city: str = None
    imitation: str = None
    year: str = None
    face: str = None
    target_audience: str = None
    rhythms_style: str = None

@router.get("/")
def get_authors(db: Session = Depends(get_db)):
    authors = db.query(Author).all()
    return [{
        "id": str(a.id),
        "name": a.author, # Keeping 'name' key for frontend backward compatibility, or mapping to author
        "author": a.author,
        "country": a.country,
        "language": a.language,
        "co_short": a.co_short,
        "city": a.city,
        "bio": a.bio,
        "imitation": a.imitation,
        "year": a.year,
        "face": a.face,
        "target_audience": a.target_audience,
        "rhythms_style": a.rhythms_style
    } for a in authors]

@router.post("/")
def create_author(author_in: AuthorCreate, db: Session = Depends(get_db)):
    new_author = Author(**author_in.model_dump())
    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    return {"id": str(new_author.id)}

@router.delete("/{author_id}")
def delete_author(author_id: str, db: Session = Depends(get_db)):
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    db.delete(author)
    db.commit()
    return {"msg": "Author deleted"}
