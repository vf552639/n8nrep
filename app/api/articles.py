from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import io

from app.database import get_db
from app.models.article import GeneratedArticle
from app.models.task import Task
from app.services.word_counter import count_content_words

router = APIRouter()


class ArticleUpdate(BaseModel):
    html_content: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None

@router.get("/")
def get_articles(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    articles = db.query(GeneratedArticle).order_by(desc(GeneratedArticle.created_at)).offset(skip).limit(limit).all()
    
    return [{
        "id": str(a.id),
        "task_id": str(a.task_id),
        "title": a.title,
        "word_count": a.word_count,
        "fact_check_status": a.fact_check_status,
        "needs_review": a.needs_review,
        "created_at": a.created_at.isoformat()
    } for a in articles]

@router.get("/{article_id}")
def get_article(article_id: str, db: Session = Depends(get_db)):
    article = db.query(GeneratedArticle).filter(GeneratedArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    task = db.query(Task).filter(Task.id == article.task_id).first()
    html = article.html_content or ""
        
    return {
        "id": str(article.id),
        "task_id": str(article.task_id),
        "title": article.title,
        "description": article.description,
        "meta_data": article.meta_data,
        "html_content": article.html_content,
        "full_page_html": article.full_page_html,
        "word_count": article.word_count,
        "fact_check_status": article.fact_check_status,
        "fact_check_issues": article.fact_check_issues,
        "needs_review": article.needs_review,
        "created_at": article.created_at.isoformat(),
        "total_cost": float(task.total_cost) if task and task.total_cost is not None else 0.0,
        "char_count": len(html),
        "main_keyword": task.main_keyword if task else "",
    }


@router.patch("/{article_id}")
def update_article(article_id: str, body: ArticleUpdate, db: Session = Depends(get_db)):
    article = db.query(GeneratedArticle).filter(GeneratedArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    data = body.model_dump(exclude_unset=True)
    if "html_content" in data and data["html_content"] is not None:
        article.html_content = data["html_content"]
        article.word_count = count_content_words(data["html_content"])
        article.full_page_html = None
    if "title" in data:
        article.title = data["title"]
    if "description" in data:
        article.description = data["description"]

    db.commit()
    db.refresh(article)

    task = db.query(Task).filter(Task.id == article.task_id).first()
    html = article.html_content or ""
    return {
        "id": str(article.id),
        "task_id": str(article.task_id),
        "title": article.title,
        "description": article.description,
        "meta_data": article.meta_data,
        "html_content": article.html_content,
        "full_page_html": article.full_page_html,
        "word_count": article.word_count,
        "fact_check_status": article.fact_check_status,
        "fact_check_issues": article.fact_check_issues,
        "needs_review": article.needs_review,
        "created_at": article.created_at.isoformat(),
        "total_cost": float(task.total_cost) if task and task.total_cost is not None else 0.0,
        "char_count": len(html),
        "main_keyword": task.main_keyword if task else "",
    }


@router.post("/{article_id}/issues/{issue_index}/resolve")
def resolve_issue(article_id: str, issue_index: int, db: Session = Depends(get_db)):
    article = db.query(GeneratedArticle).filter(GeneratedArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    issues = list(article.fact_check_issues or [])
    if issue_index < 0 or issue_index >= len(issues):
        raise HTTPException(status_code=400, detail="Invalid issue index")
        
    issues[issue_index]["resolved"] = True
    
    # Check if all critical issues are resolved to potentially unset needs_review
    # But for now simply update the JSON
    article.fact_check_issues = issues
    db.commit()
    return {"status": "ok"} 

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
