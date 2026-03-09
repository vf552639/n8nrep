from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import func
from typing import Optional
import io
import datetime

from app.database import get_db
from app.models.article import GeneratedArticle

router = APIRouter()

@router.get("/")
def get_articles(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    articles = db.query(GeneratedArticle).order_by(desc(GeneratedArticle.created_at)).offset(skip).limit(limit).all()
    
    return [{
        "id": str(a.id),
        "task_id": str(a.task_id),
        "title": a.title,
        "word_count": a.word_count,
        "created_at": a.created_at.isoformat()
    } for a in articles]

@router.get("/{article_id}")
def get_article(article_id: str, db: Session = Depends(get_db)):
    article = db.query(GeneratedArticle).filter(GeneratedArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    return {
        "id": str(article.id),
        "task_id": str(article.task_id),
        "title": article.title,
        "description": article.description,
        "html_content": article.html_content,
        "word_count": article.word_count,
        "created_at": article.created_at.isoformat()
    }

@router.get("/{article_id}/preview", response_class=HTMLResponse)
def preview_article(article_id: str, db: Session = Depends(get_db)):
    article = db.query(GeneratedArticle).filter(GeneratedArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    # Return full page template if available, otherwise just raw HTML
    return article.full_page_html or article.html_content

@router.get("/{article_id}/download")
def download_article(article_id: str, db: Session = Depends(get_db)):
    article = db.query(GeneratedArticle).filter(GeneratedArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    content = article.full_page_html or article.html_content
    file_like = io.BytesIO(content.encode("utf-8"))
    
    safe_title = "".join(x for x in (article.title or "article") if x.isalnum() or x in " -_")
    filename = f"{safe_title}.html"
    
    return StreamingResponse(
        iter([file_like.getvalue()]), 
        media_type="text/html", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
