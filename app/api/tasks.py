from typing import List, Optional
import copy
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import desc
from sqlalchemy.sql import func
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models.task import Task
from app.models.site import Site
from app.models.author import Author
from app.models.article import GeneratedArticle
from app.workers.tasks import process_generation_task
from app.config import settings
from app.services.pipeline_constants import ALL_STEPS
from app.services.serp_cache import invalidate_serp_cache
from datetime import datetime

router = APIRouter()

from typing import Literal
from pydantic import field_validator

class SerpConfig(BaseModel):
    search_engine: Literal["google", "bing", "google+bing"] = "google"
    depth: Literal[10, 20, 30, 50, 100] = 10
    device: Literal["mobile", "desktop"] = "mobile"
    os: Literal["android", "ios", "windows", "macos"] = "android"

    @field_validator("os")
    @classmethod
    def validate_os_device_combo(cls, v, info):
        device = info.data.get("device", "mobile")
        if device == "mobile" and v not in ("android", "ios"):
            raise ValueError(f"Mobile device supports only android/ios, got {v}")
        if device == "desktop" and v not in ("windows", "macos"):
            raise ValueError(f"Desktop device supports only windows/macos, got {v}")
        return v

class TaskCreate(BaseModel):
    main_keyword: str
    country: str
    language: str
    target_site: str
    author_id: Optional[int] = None
    additional_keywords: Optional[str] = None
    priority: int = 0
    page_type: str = 'article'
    serp_config: Optional[SerpConfig] = None

class TaskResponse(BaseModel):
    id: str
    main_keyword: str
    status: str
    created_at: str

    class Config:
        from_attributes = True

@router.get("/")
def get_tasks(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    site_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if site_id:
        query = query.filter(Task.target_site_id == site_id)
    if search and search.strip():
        q = f"%{search.strip()}%"
        query = query.filter(Task.main_keyword.ilike(q))

    total = query.count()
    tasks = query.order_by(desc(Task.created_at)).offset(skip).limit(limit).all()

    items = [
        {
            "id": str(t.id),
            "main_keyword": t.main_keyword,
            "country": t.country,
            "language": t.language,
            "page_type": t.page_type,
            "status": t.status,
            "total_cost": t.total_cost or 0.0,
            "target_site_id": str(t.target_site_id),
            "created_at": t.created_at.isoformat(),
            "serp_config": t.serp_config or {},
            "error_log": t.error_log,
        }
        for t in tasks
    ]
    return {"items": items, "total": total}

@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {
        "id": str(task.id),
        "main_keyword": task.main_keyword,
        "country": task.country,
        "language": task.language,
        "status": task.status,
        "total_cost": task.total_cost or 0.0,
        "page_type": task.page_type,
        "outline": task.outline,
        "serp_data": task.serp_data,
        "step_results": task.step_results or {},
        "serp_config": task.serp_config or {},
        "error_log": task.error_log,
        "created_at": task.created_at.isoformat(),
        "logs": task.logs or [],
    }

def calculate_progress(step_results: dict) -> int:
    """Progress 0–100 from _pipeline_plan when present, else legacy estimate."""
    if not step_results:
        return 0
    plan = step_results.get("_pipeline_plan")
    if isinstance(plan, dict):
        steps_order = plan.get("steps")
        if isinstance(steps_order, list) and steps_order:
            total = len(steps_order)
            done = 0
            for s in steps_order:
                block = step_results.get(s)
                if isinstance(block, dict) and block.get("status") in (
                    "completed",
                    "completed_with_warnings",
                ):
                    done += 1
            return int(min(100, (done / total) * 100))
    total_steps = 14
    completed = sum(
        1
        for k, v in (step_results or {}).items()
        if not str(k).startswith("_")
        and isinstance(v, dict)
        and v.get("status") in ("completed", "completed_with_warnings")
    )
    return int(min(100, (completed / total_steps) * 100))

@router.get("/{task_id}/steps")
def get_task_steps(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": str(task.id),
        "status": task.status,
        "total_cost": task.total_cost or 0.0,
        "progress": calculate_progress(task.step_results),
        "step_results": task.step_results or {},
        "current_step": next((k for k, v in (task.step_results or {}).items() if isinstance(v, dict) and v.get("status") == "running"), None)
    }


class UpdateStepResultRequest(BaseModel):
    step_name: str
    result: str


@router.put("/{task_id}/step-result")
def update_task_step_result(
    task_id: str,
    payload: UpdateStepResultRequest,
    db: Session = Depends(get_db),
):
    """Update the `result` of a completed pipeline step (manual edit in UI)."""
    from app.services.word_counter import count_content_words

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.step_name not in ALL_STEPS:
        raise HTTPException(status_code=400, detail=f"Invalid step_name: {payload.step_name}")

    step_results = dict(task.step_results or {})
    step_data = step_results.get(payload.step_name)
    if not isinstance(step_data, dict) or step_data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Step '{payload.step_name}' is not completed or does not exist",
        )

    prev_key = f"{payload.step_name}_prev_versions"
    if prev_key not in step_results:
        step_results[prev_key] = []
    step_results[prev_key].append(copy.deepcopy(step_data))

    updated = dict(step_data)
    updated["result"] = payload.result
    updated["manually_edited"] = True
    updated["edited_at"] = datetime.utcnow().isoformat()
    updated["output_word_count"] = count_content_words(payload.result)
    step_results[payload.step_name] = updated
    task.step_results = step_results
    flag_modified(task, "step_results")
    db.commit()
    return {"status": "ok"}


@router.get("/{task_id}/export-docx")
def export_task_docx(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    from app.services.docx_builder import build_task_export_docx

    try:
        docx_bytes = build_task_export_docx(db, task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    safe_name = (
        "".join(c for c in (task.main_keyword or "task") if c.isalnum() or c in " -_").strip()
        or "task"
    )
    filename = f"{safe_name}.docx"
    return StreamingResponse(
        iter([docx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/")
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    # Verify or create site
    site = None
    try:
        # Check if it's a valid UUID first
        uuid_obj = uuid.UUID(task_in.target_site, version=4)
        site = db.query(Site).filter(Site.id == str(uuid_obj)).first()
    except ValueError:
        pass
        
    if not site:
        site = db.query(Site).filter(
            (func.lower(Site.domain) == func.lower(task_in.target_site)) | 
            (func.lower(Site.name) == func.lower(task_in.target_site))
        ).first()
        
    if not site:
        # Automatically create the site if it wasn't found
        site = Site(
            name=task_in.target_site,
            domain=task_in.target_site,
            country=task_in.country,
            language=task_in.language,
            is_active=True
        )
        db.add(site)
        db.commit()
        db.refresh(site)

    # Auto-assign author if not provided
    final_author_id = task_in.author_id
    if not final_author_id:
        author = db.query(Author).filter(
            func.lower(Author.country) == task_in.country.lower(),
            func.lower(Author.language) == task_in.language.lower()
        ).first()
        if author:
            final_author_id = author.id

    new_task = Task(
        main_keyword=task_in.main_keyword,
        country=task_in.country,
        language=task_in.language,
        page_type=task_in.page_type,
        target_site_id=site.id,
        author_id=final_author_id,
        additional_keywords=task_in.additional_keywords,
        priority=task_in.priority,
        serp_config=task_in.serp_config.model_dump() if task_in.serp_config else None
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Dispatch Celery task (conditional on mode)
    if not settings.SEQUENTIAL_MODE:
        process_generation_task.delay(str(new_task.id))
        return {"id": str(new_task.id), "status": "Task created and queued"}
    else:
        return {"id": str(new_task.id), "status": "Task created (waiting for manual start)"}

@router.post("/bulk")
async def create_tasks_bulk(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    CSV must have columns: keyword, country, language, site_name
    """
    contents = await file.read()
    reader = csv.DictReader(io.StringIO(contents.decode('utf-8')))
    
    tasks_created = 0
    errors = []
    
    for row in reader:
        try:
            site_name = row.get("site_name")
            site = db.query(Site).filter(func.lower(Site.name) == func.lower(site_name)).first()
            if not site:
                errors.append(f"Site {site_name} not found for keyword {row['keyword']}")
                continue
                
            new_task = Task(
                main_keyword=row["keyword"],
                country=row["country"],
                language=row["language"],
                page_type=row.get("page_type", "article"),
                target_site_id=site.id
            )
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
            
            if not settings.SEQUENTIAL_MODE:
                process_generation_task.delay(str(new_task.id))
            tasks_created += 1
        except Exception as e:
            errors.append(f"Error processing row {row}: {e}")
            db.rollback()
            
    return {"tasks_created": tasks_created, "errors": errors}

@router.post("/next")
def start_next_task(db: Session = Depends(get_db)):
    """
    Берёт первую pending-задачу (по приоритету DESC, created_at ASC)
    и отправляет в Celery.
    """
    running = db.query(Task).filter(Task.status == "processing").first()
    if running:
        return {
            "status": "busy",
            "msg": "Есть задача в работе — дождитесь завершения",
            "running_task_id": str(running.id),
            "running_keyword": running.main_keyword
        }
    
    next_task = db.query(Task).filter(
        Task.status == "pending",
        Task.project_id == None
    ).order_by(
        Task.priority.desc(),
        Task.created_at.asc()
    ).first()
    
    if not next_task:
        return {"status": "empty", "msg": "Нет задач в очереди"}
    
    process_generation_task.delay(str(next_task.id))
    
    return {
        "status": "started",
        "task_id": str(next_task.id),
        "keyword": next_task.main_keyword,
        "msg": f"Задача '{next_task.main_keyword}' запущена"
    }

@router.post("/start-all")
def start_all_pending(db: Session = Depends(get_db)):
    """
    Запускает все pending-задачи (не принадлежащие проектам) в Celery последовательно (chain).
    """
    from celery import chain
    
    pending_tasks = db.query(Task).filter(
        Task.status == "pending",
        Task.project_id == None
    ).order_by(
        Task.priority.desc(),
        Task.created_at.asc()
    ).all()
    
    if not pending_tasks:
        return {"started": 0, "msg": "Нет задач в очереди"}
    
    # Celery chain — каждая задача ждёт завершения предыдущей
    task_chain = chain(
        *[process_generation_task.si(str(t.id)) for t in pending_tasks]
    )
    task_chain.apply_async()
    
    return {
        "started": len(pending_tasks), 
        "msg": f"Запущена цепочка из {len(pending_tasks)} задач (последовательно)"
    }

class StartSelectedRequest(BaseModel):
    task_ids: List[str]

@router.post("/start-selected")
def start_selected_tasks(payload: StartSelectedRequest, db: Session = Depends(get_db)):
    """
    Запускает выбранные pending-задачи в виде Celery chain (последовательно).
    """
    from celery import chain

    if not payload.task_ids:
        return {"started": 0, "msg": "Нет задач для запуска"}

    id_list: List[uuid.UUID] = []
    for tid in payload.task_ids:
        try:
            id_list.append(uuid.UUID(str(tid)))
        except ValueError:
            continue

    if not id_list:
        return {"started": 0, "msg": "Нет задач для запуска"}

    tasks = (
        db.query(Task)
        .filter(
            Task.id.in_(id_list),
            Task.status == "pending",
            Task.project_id.is_(None),
        )
        .order_by(Task.priority.desc(), Task.created_at.asc())
        .all()
    )

    if not tasks:
        return {"started": 0, "msg": "Нет задач для запуска"}

    task_chain = chain(*[process_generation_task.si(str(t.id)) for t in tasks])
    task_chain.apply_async()

    return {
        "started": len(tasks),
        "msg": f"Запущена цепочка из {len(tasks)} задач",
    }


@router.post("/delete-selected")
def delete_selected_tasks(payload: StartSelectedRequest, db: Session = Depends(get_db)):
    """Удаляет выбранные задачи и связанные статьи."""
    if not payload.task_ids:
        return {"deleted": 0}

    id_list: List[uuid.UUID] = []
    for tid in payload.task_ids:
        try:
            id_list.append(uuid.UUID(str(tid)))
        except ValueError:
            continue

    deleted = 0
    for uid in id_list:
        task = db.query(Task).filter(Task.id == uid).first()
        if not task:
            continue
        db.query(GeneratedArticle).filter(GeneratedArticle.task_id == task.id).delete(synchronize_session=False)
        db.delete(task)
        deleted += 1

    db.commit()
    return {"deleted": deleted}


@router.get("/{task_id}/serp-data")
def get_task_serp_data(task_id: str, db: Session = Depends(get_db)):
    """Возвращает структурированные SERP-данные задачи для отображения в UI."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    serp = task.serp_data or {}
    
    return {
        "source": serp.get("source", "unknown"),
        "total_results": serp.get("total_results", 0),
        "serp_features": serp.get("serp_features") or [],
        "search_intent_signals": serp.get("search_intent_signals") or {},
        "organic_results": serp.get("organic_results") or [],
        "paa_full": serp.get("paa_full") or [],
        "related_searches_full": serp.get("related_searches_full") or serp.get("related_searches") or [],
        "featured_snippet": serp.get("featured_snippet"),
        "knowledge_graph": serp.get("knowledge_graph"),
        "ai_overview": serp.get("ai_overview"),
        "answer_box": serp.get("answer_box"),
    }

@router.get("/{task_id}/serp-export")
def export_serp_csv(task_id: str, db: Session = Depends(get_db)):
    """Экспортирует SERP-данные задачи как ZIP с несколькими CSV-файлами."""
    import csv as csv_module
    import io
    import zipfile
    from fastapi.responses import StreamingResponse
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    serp = task.serp_data or {}
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. organic_results.csv
        organic = serp.get("organic_results") or []
        if organic:
            csv_buf = io.StringIO()
            fieldnames = ["rank_group", "rank_absolute", "title", "url", "domain",
                          "description", "is_featured_snippet", "highlighted"]
            writer = csv_module.DictWriter(csv_buf, fieldnames=fieldnames)
            writer.writeheader()
            for r in organic:
                row = {k: r.get(k, "") for k in fieldnames}
                row["highlighted"] = "; ".join(r.get("highlighted") or [])
                writer.writerow(row)
            zf.writestr("organic_results.csv", csv_buf.getvalue())
        
        # 2. paa.csv
        paa = serp.get("paa_full") or []
        if paa:
            csv_buf = io.StringIO()
            fieldnames = ["question", "answer", "url", "domain"]
            writer = csv_module.DictWriter(csv_buf, fieldnames=fieldnames)
            writer.writeheader()
            for p in paa:
                writer.writerow({k: p.get(k, "") for k in fieldnames})
            zf.writestr("paa.csv", csv_buf.getvalue())
        
        # 3. related_searches.csv
        related = serp.get("related_searches_full") or serp.get("related_searches") or []
        if related:
            csv_buf = io.StringIO()
            if related and isinstance(related[0], dict):
                writer = csv_module.DictWriter(csv_buf, fieldnames=["query", "highlighted"])
                writer.writeheader()
                for rs in related:
                    row = {"query": rs.get("query", ""), "highlighted": "; ".join(rs.get("highlighted") or [])}
                    writer.writerow(row)
            else:
                writer = csv_module.writer(csv_buf)
                writer.writerow(["query"])
                for rs in related:
                    writer.writerow([rs])
            zf.writestr("related_searches.csv", csv_buf.getvalue())
        
        # 4. snippets.csv
        snippets_rows = []
        fs = serp.get("featured_snippet")
        if fs:
            snippets_rows.append({
                "type": "featured_snippet", "title": fs.get("title", ""),
                "text": fs.get("description", ""), "url": fs.get("url", ""),
                "domain": fs.get("domain", ""), "snippet_type": fs.get("type", ""),
            })
        ab = serp.get("answer_box")
        if ab:
            snippets_rows.append({
                "type": "answer_box", "title": "",
                "text": ab.get("text", ""), "url": ab.get("url", ""),
                "domain": "", "snippet_type": ab.get("type", ""),
            })
        ai_ov = serp.get("ai_overview")
        if ai_ov:
            snippets_rows.append({
                "type": "ai_overview", "title": "",
                "text": ai_ov.get("text", "")[:5000], "url": "",
                "domain": "", "snippet_type": "",
            })
        if snippets_rows:
            csv_buf = io.StringIO()
            fieldnames = ["type", "title", "text", "url", "domain", "snippet_type"]
            writer = csv_module.DictWriter(csv_buf, fieldnames=fieldnames)
            writer.writeheader()
            for row in snippets_rows:
                writer.writerow(row)
            zf.writestr("snippets.csv", csv_buf.getvalue())
        
        # 5. knowledge_graph.csv
        kg = serp.get("knowledge_graph")
        if kg:
            csv_buf = io.StringIO()
            writer = csv_module.writer(csv_buf)
            writer.writerow(["field", "value"])
            writer.writerow(["title", kg.get("title", "")])
            writer.writerow(["subtitle", kg.get("subtitle", "")])
            writer.writerow(["description", kg.get("description", "")])
            for fact in kg.get("facts") or []:
                writer.writerow([fact.get("label", ""), fact.get("value", "")])
            zf.writestr("knowledge_graph.csv", csv_buf.getvalue())
        
        # 6. serp_meta.csv
        csv_buf = io.StringIO()
        writer = csv_module.writer(csv_buf)
        writer.writerow(["key", "value"])
        writer.writerow(["source", serp.get("source", "")])
        writer.writerow(["total_results", serp.get("total_results", 0)])
        writer.writerow(["serp_features", "; ".join(serp.get("serp_features") or [])])
        signals = serp.get("search_intent_signals") or {}
        for k, v in signals.items():
            writer.writerow([k, v])
        zf.writestr("serp_meta.csv", csv_buf.getvalue())
    
    zip_buffer.seek(0)
    safe_keyword = "".join(c for c in (task.main_keyword or "serp") if c.isalnum() or c in " -_")
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=serp_{safe_keyword}.zip"}
    )

@router.post("/{task_id}/retry")
def retry_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "failed":
        raise HTTPException(status_code=400, detail="Can only retry failed tasks")
        
    task.status = "pending"
    task.error_log = None
    task.retry_count += 1
    db.commit()
    
    process_generation_task.delay(str(task.id))
    return {"msg": "Task queued for retry"}


@router.delete("/{task_id}/cache")
def clear_task_cache(task_id: str, db: Session = Depends(get_db)):
    """Invalidate SERP cache key for this task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    deleted = invalidate_serp_cache(
        keyword=task.main_keyword,
        country_code=task.country,
        language_code=task.language,
        serp_config=task.serp_config or {},
    )
    return {"msg": "Task cache invalidated", "serp_cache_deleted": bool(deleted)}

@router.post("/{task_id}/approve")
def approve_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Check if we are waiting for approval
    step_results = dict(task.step_results or {})
    if not step_results.get("waiting_for_approval"):
        raise HTTPException(status_code=400, detail="Task is not waiting for approval")
        
    # Mark as approved and remove the waiting flag
    step_results["waiting_for_approval"] = False
    step_results["test_mode_approved"] = True
    task.step_results = step_results
    
    # Needs to be back in processing or pending to resume cleanly
    task.status = "pending" 
    db.commit()
    
    # Resume pipeline
    process_generation_task.delay(str(task.id))
    return {"msg": "Task approved and queued for continuation"}

@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    db.delete(task)
    db.commit()
    return {"msg": "Task deleted"}

class ForceStatusRequest(BaseModel):
    action: str  # "complete" or "fail"

@router.post("/{task_id}/force-status")
def force_task_status(task_id: str, payload: ForceStatusRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status not in ("processing", "stale"):
        raise HTTPException(
            status_code=400,
            detail="Only 'processing' or 'stale' tasks can be forced",
        )
        
    if payload.action == "fail":
        task.status = "failed"
        task.error_log = "Force-failed by user"
        db.commit()
        return {"msg": "Task forcefully marked as failed"}
    elif payload.action == "complete":
        if not task.step_results:
            raise HTTPException(status_code=400, detail="Task has no step results, cannot force complete")
        task.status = "completed"
        db.commit()
        return {"msg": "Task forcefully marked as completed"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'complete' or 'fail'")

class RerunStepRequest(BaseModel):
    step_name: str
    feedback: str
    cascade: bool = True

@router.post("/{task_id}/rerun-step")
def rerun_task_step(task_id: str, payload: RerunStepRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status not in ("completed", "processing", "failed", "pending"):
        raise HTTPException(status_code=400, detail="Task status does not allow rerunning steps")
        
    step_results = dict(task.step_results or {})
    if payload.step_name not in step_results or step_results[payload.step_name].get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Step '{payload.step_name}' is not completed or does not exist")
        
    invalidated_steps = []
    
    if payload.cascade:
        try:
            step_idx = ALL_STEPS.index(payload.step_name)
            steps_to_remove = ALL_STEPS[step_idx:]
        except ValueError:
            steps_to_remove = [payload.step_name]
            
        for s in steps_to_remove:
            if s in step_results:
                invalidated_steps.append(s)
                del step_results[s]
                
        # Delete generated article if exists since we are cascading
        article = db.query(GeneratedArticle).filter(GeneratedArticle.task_id == task_id).first()
        if article:
            db.delete(article)
    else:
        invalidated_steps.append(payload.step_name)
        del step_results[payload.step_name]
        
        # Image chain special-casing:
        # - image_prompt_generation -> affects image_generation -> image_inject
        # - image_generation -> affects image_inject
        # - Do NOT invalidate primary_generation or later steps here (no cascade),
        #   only re-run the minimal dependent steps inside the image chain.
        if payload.step_name == "image_prompt_generation":
            for s in ("image_generation", "image_inject"):
                if s in step_results:
                    invalidated_steps.append(s)
                    del step_results[s]
        elif payload.step_name == "image_generation":
            if "image_inject" in step_results:
                invalidated_steps.append("image_inject")
                del step_results["image_inject"]
    
    # --- Clear cached data so pipeline phases re-fetch ---
    try:
        serp_idx = ALL_STEPS.index("serp_research")
        scraping_idx = ALL_STEPS.index("competitor_scraping")
        rerun_idx = ALL_STEPS.index(payload.step_name)
    except ValueError:
        rerun_idx = -1
        serp_idx = -1
        scraping_idx = -1

    if rerun_idx <= serp_idx:
        invalidate_serp_cache(
            keyword=task.main_keyword,
            country_code=task.country,
            language_code=task.language,
            serp_config=task.serp_config or {},
        )
        task.serp_data = None
        task.competitors_text = None
        task.outline = None
    elif rerun_idx <= scraping_idx:
        task.competitors_text = None
        task.outline = None
        
    # Save feedback
    step_results["_rerun_feedback"] = {
        "step": payload.step_name,
        "feedback": payload.feedback,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Store previous version of the step for history
    prev_versions_key = f"{payload.step_name}_prev_versions"
    if prev_versions_key not in step_results:
        step_results[prev_versions_key] = []
        
    # We retrieve the actual previous output from the DB task before it was deleted in step_results
    old_step_data = task.step_results.get(payload.step_name)
    if old_step_data:
        step_results[prev_versions_key].append(old_step_data)
        
    task.step_results = step_results
    task.status = "pending"
    
    # Log the action
    log_msg = f"🔄 Rerun requested for step '{payload.step_name}' with feedback: '{payload.feedback[:200]}'. Cascade: {payload.cascade}. Invalidated steps: {invalidated_steps}"
    
    logs = list(task.logs or [])
    logs.append({
        "timestamp": datetime.utcnow().isoformat(),
        "level": "info",
        "step": payload.step_name,
        "message": log_msg
    })
    task.logs = logs
    
    db.commit()
    
    process_generation_task.delay(str(task.id))
    
    return {
        "msg": f"Step '{payload.step_name}' queued for re-run",
        "invalidated_steps": invalidated_steps
    }

# ========================
# IMAGE REVIEW ENDPOINTS
# ========================

@router.get("/{task_id}/images")
def get_task_images(task_id: str, db: Session = Depends(get_db)):
    """Get generated images for review."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    step_results = task.step_results or {}
    image_gen_result = step_results.get("image_generation", {}).get("result", "")
    
    if not image_gen_result:
        return {"images": [], "summary": {}, "paused": False}

    import json as _json
    try:
        data = _json.loads(image_gen_result) if isinstance(image_gen_result, str) else image_gen_result
    except Exception:
        data = {"images": []}

    pause_state = step_results.get("_pipeline_pause", {})
    is_paused = isinstance(pause_state, dict) and pause_state.get("active") and pause_state.get("reason") == "image_review"

    return {
        "images": data.get("images", []),
        "summary": data.get("summary", {}),
        "paused": is_paused,
    }


class ApproveImagesRequest(BaseModel):
    approved_ids: list  # List of image IDs to approve
    skipped_ids: list = []  # List of image IDs to skip


@router.post("/{task_id}/approve-images")
def approve_images(task_id: str, payload: ApproveImagesRequest, db: Session = Depends(get_db)):
    """Approve/skip images and resume pipeline."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    step_results = dict(task.step_results or {})
    image_gen_result = step_results.get("image_generation", {}).get("result", "")

    if not image_gen_result:
        raise HTTPException(status_code=400, detail="No image generation data found")

    import json as _json
    try:
        data = _json.loads(image_gen_result) if isinstance(image_gen_result, str) else image_gen_result
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse image data")

    images = data.get("images", [])
    approved_set = set(payload.approved_ids)
    skipped_set = set(payload.skipped_ids)

    for img in images:
        if img["id"] in approved_set:
            img["approved"] = True
        elif img["id"] in skipped_set:
            img["approved"] = False

    # Save updated image data
    step_data = dict(step_results.get("image_generation", {}))
    step_data["result"] = _json.dumps(data, ensure_ascii=False)
    step_results["image_generation"] = step_data

    # Clear the pause
    step_results["_pipeline_pause"] = {"active": False, "reason": "image_review"}
    step_results["_images_approved"] = True
    task.step_results = step_results
    task.status = "pending"
    db.commit()

    # Resume pipeline
    process_generation_task.delay(str(task.id))

    return {
        "msg": f"Images reviewed: {len(approved_set)} approved, {len(skipped_set)} skipped. Pipeline resumed.",
        "approved_count": len(approved_set),
        "skipped_count": len(skipped_set),
    }


class RegenerateImageRequest(BaseModel):
    image_id: str
    new_prompt: str = ""  # Optional prompt override


@router.post("/{task_id}/regenerate-image")
def regenerate_image(task_id: str, payload: RegenerateImageRequest, db: Session = Depends(get_db)):
    """Regenerate a specific image (while pipeline is paused)."""
    from app.services.image_generator import OpenRouterImageGenerator, resolve_image_generation_model
    from app.services.image_hosting import ImgBBUploader

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    step_results = dict(task.step_results or {})
    image_gen_result = step_results.get("image_generation", {}).get("result", "")

    if not image_gen_result:
        raise HTTPException(status_code=400, detail="No image generation data found")

    import json as _json
    try:
        data = _json.loads(image_gen_result) if isinstance(image_gen_result, str) else image_gen_result
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse image data")

    images = data.get("images", [])
    target_img = next((img for img in images if img["id"] == payload.image_id), None)
    if not target_img:
        raise HTTPException(status_code=404, detail=f"Image '{payload.image_id}' not found")

    prompt = payload.new_prompt or target_img.get("image_prompt") or target_img.get("midjourney_prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt available for regeneration")

    if not settings.OPENROUTER_API_KEY:
        raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not configured")

    try:
        model_id = resolve_image_generation_model(db)
        fallback_model = settings.IMAGE_MODEL_DEFAULT if model_id != settings.IMAGE_MODEL_DEFAULT else None
        generator = OpenRouterImageGenerator(
            api_key=settings.OPENROUTER_API_KEY,
            model=model_id,
            fallback_model=fallback_model,
        )
        result = generator.generate_and_wait(
            prompt=prompt,
            aspect_ratio=target_img.get("aspect_ratio", "16:9"),
        )

        if result.status == "completed" and result.image_url:
            uploader = ImgBBUploader(api_key=settings.IMGBB_API_KEY)
            keyword_slug = task.main_keyword.lower().replace(" ", "-")[:30]
            filename = f"regen_{keyword_slug}_{payload.image_id}"
            hosted = uploader.upload_from_data_url(result.image_url, filename)

            target_img["status"] = "completed"
            target_img["original_url"] = None
            target_img["hosted_url"] = hosted.get("url", "")
            target_img["error"] = None
            if payload.new_prompt:
                target_img["image_prompt"] = payload.new_prompt
                target_img["midjourney_prompt"] = payload.new_prompt
        else:
            target_img["status"] = "failed"
            target_img["error"] = result.error or "Regeneration failed"

    except Exception as e:
        target_img["status"] = "failed"
        target_img["error"] = str(e)

    step_data = dict(step_results.get("image_generation", {}))
    step_data["result"] = _json.dumps(data, ensure_ascii=False)
    step_results["image_generation"] = step_data
    task.step_results = step_results
    db.commit()

    return {"image": target_img}

