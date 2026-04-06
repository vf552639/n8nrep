from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.sql import func
from typing import Optional, Any, Dict, List, Tuple
from collections import defaultdict
from pydantic import BaseModel
import uuid
import os
import csv
import io
from datetime import datetime

from app.database import get_db
from app.api.tasks import calculate_progress
from app.models.project import SiteProject
from app.models.blueprint import SiteBlueprint, BlueprintPage
from app.models.site import Site
from app.models.template import Template
from app.models.author import Author
from app.models.task import Task
from app.models.article import GeneratedArticle
from app.workers.celery_app import celery_app

# Imported to defer circular dep issues, will verify app.workers.tasks is available
from app.workers.tasks import process_site_project, advance_project
from app.config import settings
from app.services.pipeline_presets import pipeline_steps_use_serp, resolve_pipeline_steps

router = APIRouter()


def _validate_serp_config(cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and normalize SERP config; returns dict (possibly empty)."""
    if not cfg:
        return {}
    allowed_engines = {"google", "bing", "google+bing"}
    allowed_depths = {10, 20, 30, 50, 100}
    allowed_devices = {"mobile", "desktop"}
    allowed_os = {"android", "ios", "windows", "macos"}

    engine = cfg.get("search_engine", "google")
    if engine not in allowed_engines:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid search_engine: {engine}. Allowed: {sorted(allowed_engines)}",
        )

    depth = cfg.get("depth", 10)
    if depth not in allowed_depths:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid depth: {depth}. Allowed: {sorted(allowed_depths)}",
        )

    device = cfg.get("device", "mobile")
    if device not in allowed_devices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid device: {device}. Allowed: {sorted(allowed_devices)}",
        )

    os_val = cfg.get("os", "android")
    if os_val not in allowed_os:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid os: {os_val}. Allowed: {sorted(allowed_os)}",
        )

    return {
        "search_engine": engine,
        "depth": depth,
        "device": device,
        "os": os_val,
    }


def _resolve_site_readonly(
    db: Session, target_site: str
) -> Tuple[Optional[Site], bool, str, str]:
    """
    Resolve site by UUID or domain/name without creating.
    Returns (site_or_none, will_be_created, name, domain).
    """
    site = None
    try:
        uuid_obj = uuid.UUID(target_site, version=4)
        site = db.query(Site).filter(Site.id == str(uuid_obj)).first()
    except ValueError:
        pass

    if not site:
        site = db.query(Site).filter(
            (func.lower(Site.domain) == func.lower(target_site))
            | (func.lower(Site.name) == func.lower(target_site))
        ).first()

    if site:
        return site, False, site.name, site.domain
    return None, True, target_site, target_site


def _resolve_site(db: Session, target_site: str, country: str, language: str) -> Site:
    """Resolve site by UUID or domain/name; create if missing."""
    site = None
    try:
        uuid_obj = uuid.UUID(target_site, version=4)
        site = db.query(Site).filter(Site.id == str(uuid_obj)).first()
    except ValueError:
        pass

    if not site:
        site = db.query(Site).filter(
            (func.lower(Site.domain) == func.lower(target_site))
            | (func.lower(Site.name) == func.lower(target_site))
        ).first()

    if not site:
        site = Site(
            name=target_site,
            domain=target_site,
            country=country,
            language=language,
            is_active=True,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
    return site


def _ensure_worker_available() -> None:
    try:
        inspect = celery_app.control.inspect(timeout=3)
        ping = inspect.ping()
        if not ping:
            raise HTTPException(
                status_code=503,
                detail="Worker недоступен. Проверьте docker-compose logs worker.",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Не удалось проверить доступность worker. Проверьте Redis и Celery worker.",
        )


def _task_cost_sum(tasks: List[Task]) -> float:
    return float(sum((t.total_cost or 0) for t in tasks))


def _project_detail_extras(
    project: SiteProject, tasks: List[Task], blueprint_page_count: int
) -> Dict[str, Any]:
    completed_n = sum(1 for t in tasks if t.status == "completed")
    total_cost = _task_cost_sum(tasks)
    avg_cost_per_page = round(total_cost / max(completed_n, 1), 4) if tasks else 0.0
    duration_seconds = None
    if project.started_at and project.completed_at:
        duration_seconds = (project.completed_at - project.started_at).total_seconds()
    avg_seconds_per_page = None
    if duration_seconds is not None and completed_n:
        avg_seconds_per_page = round(duration_seconds / completed_n, 2)
    remaining_pages = max(0, blueprint_page_count - completed_n)
    return {
        "total_cost": round(total_cost, 4),
        "avg_cost_per_page": avg_cost_per_page,
        "started_at": project.started_at.isoformat() if project.started_at else None,
        "generation_started_at": project.generation_started_at.isoformat() if getattr(project, "generation_started_at", None) else None,
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        "duration_seconds": duration_seconds,
        "avg_seconds_per_page": avg_seconds_per_page,
        "blueprint_page_count": blueprint_page_count,
        "remaining_pages": remaining_pages,
        "logs": project.logs if isinstance(project.logs, list) else (project.logs or []),
    }

class SiteProjectCreate(BaseModel):
    name: str
    blueprint_id: str
    seed_keyword: str
    seed_is_brand: bool = False
    target_site: str  # Domain or name
    country: str
    language: str
    author_id: Optional[int] = None
    serp_config: Optional[Dict[str, Any]] = None
    project_keywords: Optional[Dict[str, Any]] = None


class ClusterKeywordsRequest(BaseModel):
    keywords: List[str]
    blueprint_id: str


class ProjectPreviewRequest(BaseModel):
    blueprint_id: str
    seed_keyword: str
    seed_is_brand: bool = False
    target_site: str
    country: str
    language: str
    author_id: Optional[int] = None
    serp_config: Optional[Dict[str, Any]] = None


class SiteProjectCloneBody(BaseModel):
    name: Optional[str] = None
    seed_keyword: Optional[str] = None
    seed_is_brand: Optional[bool] = None
    target_site: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    author_id: Optional[int] = None

class SiteProjectResponse(BaseModel):
    id: str
    name: str
    blueprint_id: str
    site_id: str
    seed_keyword: str
    seed_is_brand: bool
    status: str
    current_page_index: int
    build_zip_url: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True

@router.get("/")
def get_projects(
    skip: int = 0,
    limit: int = 50,
    archived: bool = False,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(SiteProject).filter(SiteProject.is_archived == archived)
    if status:
        q = q.filter(SiteProject.status == status)
    if search:
        q = q.filter(SiteProject.name.ilike(f"%{search}%"))
    projects = q.order_by(desc(SiteProject.created_at)).offset(skip).limit(limit).all()
    if not projects:
        return []

    project_ids = [p.id for p in projects]
    task_rows = db.query(Task).filter(Task.project_id.in_(project_ids)).all()
    by_project = defaultdict(list)
    for t in task_rows:
        by_project[str(t.project_id)].append(t)

    out = []
    for p in projects:
        tasks = by_project.get(str(p.id), [])
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "completed")
        failed_n = sum(1 for t in tasks if t.status == "failed")
        progress = round((completed / total) * 100) if total > 0 else 0
        total_cost = round(_task_cost_sum(tasks), 4)
        out.append({
            "id": str(p.id),
            "name": p.name,
            "blueprint_id": str(p.blueprint_id),
            "site_id": str(p.site_id),
            "seed_keyword": p.seed_keyword,
            "seed_is_brand": getattr(p, "seed_is_brand", False),
            "status": p.status,
            "current_page_index": p.current_page_index,
            "build_zip_url": p.build_zip_url,
            "created_at": p.created_at.isoformat(),
            "progress": progress,
            "generation_started_at": p.generation_started_at.isoformat() if getattr(p, "generation_started_at", None) else None,
            "is_archived": bool(getattr(p, "is_archived", False)),
            "country": p.country,
            "language": p.language,
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed_n,
            "total_cost": total_cost,
            "serp_config": getattr(p, "serp_config", None) or {},
        })
    return out


@router.post("/preview")
def preview_project(body: ProjectPreviewRequest, db: Session = Depends(get_db)):
    blueprint = db.query(SiteBlueprint).filter(SiteBlueprint.id == body.blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    pages = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.blueprint_id == body.blueprint_id)
        .order_by(BlueprintPage.sort_order)
        .all()
    )

    site, site_will_create, site_name, site_domain = _resolve_site_readonly(db, body.target_site)
    warnings: List[str] = []

    if site is None:
        warnings.append(
            f"Site '{body.target_site}' not found — will be created automatically"
        )

    has_template = False
    if site is not None and site.template_id:
        tpl = (
            db.query(Template)
            .filter(Template.id == site.template_id, Template.is_active == True)  # noqa: E712
            .first()
        )
        has_template = tpl is not None
        if not has_template:
            warnings.append("Site template_id is set but template is missing or inactive.")
    elif site is not None:
        warnings.append("Site has no HTML template. Articles will be generated without site wrapper.")

    author_source = "none"
    author_id: Optional[int] = None
    author_name: Optional[str] = None

    if body.author_id is not None:
        au = db.query(Author).filter(Author.id == body.author_id).first()
        if au:
            author_id = int(au.id)
            author_name = (au.author or "").strip() or str(au.id)
            author_source = "manual"
        else:
            warnings.append("Given author_id not found; will try auto-assign.")
    if author_id is None:
        au = db.query(Author).filter(
            func.lower(Author.country) == body.country.lower(),
            func.lower(Author.language) == body.language.lower(),
        ).first()
        if au:
            author_id = int(au.id)
            author_name = (au.author or "").strip() or str(au.id)
            author_source = "auto"
        else:
            warnings.append(
                f"No author found for {body.country}/{body.language}. Tasks will have no author assigned."
            )

    if len(pages) == 0:
        warnings.append("Blueprint has no pages defined.")

    serp_cfg = {}
    if body.serp_config is not None:
        serp_cfg = _validate_serp_config(body.serp_config)

    page_rows = []
    for pg in pages:
        use_brand = bool(body.seed_is_brand) and bool(getattr(pg, "keyword_template_brand", None))
        template_used = "brand" if use_brand else "standard"
        tmpl = (
            pg.keyword_template_brand
            if use_brand and pg.keyword_template_brand
            else pg.keyword_template
        )
        kw = tmpl.replace("{seed}", body.seed_keyword)
        _steps = resolve_pipeline_steps(pg)
        page_rows.append(
            {
                "sort_order": pg.sort_order,
                "page_slug": pg.page_slug,
                "page_title": pg.page_title,
                "page_type": pg.page_type,
                "keyword": kw,
                "template_used": template_used,
                "use_serp": pipeline_steps_use_serp(_steps),
                "pipeline_preset": getattr(pg, "pipeline_preset", "full") or "full",
                "filename": pg.filename,
            }
        )

    recent_costs = (
        db.query(Task.total_cost)
        .filter(Task.status == "completed", Task.total_cost > 0)
        .order_by(desc(Task.created_at))
        .limit(50)
        .all()
    )
    costs = [float(r[0]) for r in recent_costs if r[0] is not None]
    avg_cost_per_page = round(sum(costs) / len(costs), 4) if costs else None
    n_pages = len(pages)
    estimated_cost = (
        round(avg_cost_per_page * n_pages, 4)
        if avg_cost_per_page is not None and n_pages
        else None
    )

    from app.services.serp import get_serp_health

    serp_health = get_serp_health()
    overall = serp_health.get("overall")
    if overall == "error":
        warnings.append(
            "⚠️ SERP providers are partially or fully unavailable. Pages with SERP may fail."
        )
    if overall == "unconfigured":
        warnings.append(
            "⚠️ No SERP API keys configured. SERP-dependent pages will fail."
        )

    return {
        "blueprint": {
            "id": str(blueprint.id),
            "name": blueprint.name,
            "total_pages": n_pages,
        },
        "site": {
            "id": str(site.id) if site else None,
            "name": site_name,
            "domain": site_domain,
            "has_template": has_template if site is not None else False,
            "will_be_created": site_will_create,
        },
        "author": {
            "id": author_id,
            "name": author_name,
            "source": author_source,
        },
        "pages": page_rows,
        "warnings": warnings,
        "estimated_cost": estimated_cost,
        "avg_cost_per_page": avg_cost_per_page,
        "serp_config": serp_cfg,
        "serp_health": serp_health,
    }


@router.post("/cluster-keywords")
def cluster_project_keywords(body: ClusterKeywordsRequest, db: Session = Depends(get_db)):
    if len(body.keywords) == 0:
        raise HTTPException(status_code=400, detail="At least 1 keyword required")
    if len(body.keywords) > settings.MAX_PROJECT_KEYWORDS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_PROJECT_KEYWORDS} keywords allowed",
        )

    blueprint = db.query(SiteBlueprint).filter(SiteBlueprint.id == body.blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    pages = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.blueprint_id == body.blueprint_id)
        .order_by(BlueprintPage.sort_order)
        .all()
    )
    if not pages:
        raise HTTPException(status_code=400, detail="Blueprint has no pages")

    from app.services.keyword_clusterer import cluster_keywords

    return cluster_keywords(
        keywords=body.keywords,
        pages=[
            {
                "slug": p.page_slug,
                "title": p.page_title,
                "keyword_template": p.keyword_template,
                "page_type": p.page_type,
            }
            for p in pages
        ],
    )


@router.post("/")
def create_project(project_in: SiteProjectCreate, db: Session = Depends(get_db)):
    # Verify blueprint
    blueprint = db.query(SiteBlueprint).filter(SiteBlueprint.id == project_in.blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    site = _resolve_site(db, project_in.target_site, project_in.country, project_in.language)

    existing = (
        db.query(SiteProject)
        .filter(
            SiteProject.blueprint_id == blueprint.id,
            SiteProject.seed_keyword == project_in.seed_keyword,
            SiteProject.site_id == site.id,
            SiteProject.is_archived == False,  # noqa: E712
            SiteProject.status.not_in(["failed"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    f"Active project with same blueprint + seed + site already exists "
                    f"(status: {existing.status})"
                ),
                "existing_project_id": str(existing.id),
            },
        )

    serp_normalized: Dict[str, Any] = {}
    if project_in.serp_config is not None:
        serp_normalized = _validate_serp_config(project_in.serp_config)

    pk_val: Optional[Dict[str, Any]] = None
    if project_in.project_keywords is not None:
        d = project_in.project_keywords
        if isinstance(d, dict):
            raw = d.get("raw")
            if isinstance(raw, list) and len(raw) > settings.MAX_PROJECT_KEYWORDS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Maximum {settings.MAX_PROJECT_KEYWORDS} keywords allowed",
                )
        pk_val = project_in.project_keywords

    # Auto-assign author
    final_author_id = project_in.author_id
    if not final_author_id:
        author = db.query(Author).filter(
            func.lower(Author.country) == project_in.country.lower(),
            func.lower(Author.language) == project_in.language.lower(),
        ).first()
        if author:
            final_author_id = author.id

    new_project = SiteProject(
        name=project_in.name,
        blueprint_id=blueprint.id,
        site_id=site.id,
        seed_keyword=project_in.seed_keyword,
        country=project_in.country,
        language=project_in.language,
        author_id=final_author_id,
        seed_is_brand=project_in.seed_is_brand,
        status="pending",
        serp_config=serp_normalized or {},
        project_keywords=pk_val,
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    _ensure_worker_available()

    result = process_site_project.delay(str(new_project.id))
    new_project.celery_task_id = result.id
    db.commit()

    serp_warning = None
    try:
        from app.services.serp import get_serp_health

        health = get_serp_health()
        if health.get("overall") == "error":
            providers_down = [
                k
                for k, v in health.items()
                if isinstance(v, dict) and v.get("status") == "error"
            ]
            serp_warning = (
                f"SERP providers may be unavailable: {', '.join(providers_down)}. "
                "Some pages may fail."
            )
        elif health.get("overall") == "unconfigured":
            serp_warning = (
                "No SERP providers configured. Pages with use_serp=true will fail."
            )
    except Exception:
        pass

    return {
        "id": str(new_project.id),
        "status": "Project created and queued",
        "serp_warning": serp_warning,
    }


@router.get("/{id}/export-csv")
def export_project_csv(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = db.query(Task).filter(Task.project_id == id).order_by(Task.created_at).all()
    task_ids = [t.id for t in tasks]
    blueprint_page_ids = [t.blueprint_page_id for t in tasks if t.blueprint_page_id]

    articles_map: Dict[str, GeneratedArticle] = {}
    if task_ids:
        articles = (
            db.query(GeneratedArticle).filter(GeneratedArticle.task_id.in_(task_ids)).all()
        )
        for a in articles:
            articles_map[str(a.task_id)] = a

    pages_map: Dict[str, BlueprintPage] = {}
    if blueprint_page_ids:
        bp_pages = (
            db.query(BlueprintPage).filter(BlueprintPage.id.in_(blueprint_page_ids)).all()
        )
        for p in bp_pages:
            pages_map[str(p.id)] = p

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "page_slug",
            "keyword",
            "page_type",
            "status",
            "filename",
            "title",
            "description",
            "word_count",
            "cost",
            "fact_check",
            "created_at",
        ]
    )

    for task in tasks:
        bp_page = pages_map.get(str(task.blueprint_page_id)) if task.blueprint_page_id else None
        article = articles_map.get(str(task.id))
        writer.writerow(
            [
                bp_page.page_slug if bp_page else "",
                task.main_keyword,
                task.page_type,
                str(task.status),
                bp_page.filename if bp_page else "",
                article.title if article else "",
                article.description if article else "",
                article.word_count if article else "",
                f"{task.total_cost:.4f}" if task.total_cost else "0.0000",
                article.fact_check_status if article else "",
                task.created_at.isoformat() if task.created_at else "",
            ]
        )

    writer.writerow([])
    writer.writerow(
        [
            "TOTAL",
            "",
            "",
            f"{sum(1 for t in tasks if t.status == 'completed')}/{len(tasks)} completed",
            "",
            "",
            "",
            sum(a.word_count or 0 for a in articles_map.values()),
            f"{sum(t.total_cost or 0 for t in tasks):.4f}",
            "",
            "",
        ]
    )

    safe_name = "".join(c for c in project.name if c.isalnum() or c in " -_").strip().replace(" ", "_")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="project_{safe_name}.csv"',
        },
    )


@router.get("/{id}/export-docx")
def export_project_docx(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    n_done = (
        db.query(func.count(Task.id))
        .filter(Task.project_id == id, Task.status == "completed")
        .scalar()
        or 0
    )
    if n_done == 0:
        raise HTTPException(status_code=400, detail="No completed pages to export")

    from app.services.docx_builder import build_project_docx

    docx_bytes = build_project_docx(db, str(project.id))
    safe_name = (
        "".join(c for c in project.name if c.isalnum() or c in " -_").strip() or "project"
    )
    filename = f"{safe_name}.docx"
    return StreamingResponse(
        iter([docx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{id}")
def get_project_details(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = db.query(Task).filter(Task.project_id == id).order_by(Task.created_at).all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "completed")
    failed_count = sum(1 for t in tasks if t.status == "failed")
    progress_pct = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    blueprint_page_count = (
        db.query(func.count(BlueprintPage.id))
        .filter(BlueprintPage.blueprint_id == project.blueprint_id)
        .scalar()
        or 0
    )
    extras = _project_detail_extras(project, tasks, int(blueprint_page_count))

    return {
        "id": str(project.id),
        "name": project.name,
        "blueprint_id": str(project.blueprint_id),
        "site_id": str(project.site_id),
        "seed_keyword": project.seed_keyword,
        "seed_is_brand": bool(getattr(project, "seed_is_brand", False)),
        "status": project.status,
        "current_page_index": project.current_page_index,
        "build_zip_url": project.build_zip_url,
        "stopping_requested": project.stopping_requested,
        "error_log": project.error_log,
        "progress": progress_pct,
        "failed_count": failed_count,
        "is_archived": bool(getattr(project, "is_archived", False)),
        "created_at": project.created_at.isoformat(),
        "generation_started_at": project.generation_started_at.isoformat() if getattr(project, "generation_started_at", None) else None,
        "celery_task_id": project.celery_task_id,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "serp_config": getattr(project, "serp_config", None) or {},
        "project_keywords": project.project_keywords
        if isinstance(getattr(project, "project_keywords", None), dict)
        else None,
        **extras,
        "tasks": [
            {
                "id": str(t.id),
                "blueprint_page_id": str(t.blueprint_page_id) if t.blueprint_page_id else None,
                "status": t.status,
                "main_keyword": t.main_keyword,
                "page_type": t.page_type,
                "progress": calculate_progress(t.step_results),
                "current_step": next(
                    (
                        k
                        for k, v in (t.step_results or {}).items()
                        if isinstance(v, dict) and v.get("status") == "running"
                    ),
                    None,
                ),
            }
            for t in tasks
        ],
    }


@router.post("/{id}/archive")
def archive_project(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.is_archived = True
    db.commit()
    return {"msg": "Project archived", "project_id": str(project.id), "is_archived": True}


@router.post("/{id}/clone")
def clone_project(id: str, body: SiteProjectCloneBody, db: Session = Depends(get_db)):
    src = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Project not found")

    name = body.name if body.name is not None else f"{src.name} (copy)"
    seed_keyword = body.seed_keyword if body.seed_keyword is not None else src.seed_keyword
    seed_is_brand = body.seed_is_brand if body.seed_is_brand is not None else bool(
        getattr(src, "seed_is_brand", False)
    )
    country = body.country if body.country is not None else src.country
    language = body.language if body.language is not None else src.language

    if body.target_site is not None:
        site = _resolve_site(db, body.target_site, country, language)
    else:
        site = db.query(Site).filter(Site.id == src.site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found for project")

    author_id = body.author_id if body.author_id is not None else src.author_id
    if author_id is None:
        author = db.query(Author).filter(
            func.lower(Author.country) == country.lower(),
            func.lower(Author.language) == language.lower(),
        ).first()
        if author:
            author_id = author.id

    dup = (
        db.query(SiteProject)
        .filter(
            SiteProject.blueprint_id == src.blueprint_id,
            SiteProject.seed_keyword == seed_keyword,
            SiteProject.site_id == site.id,
            SiteProject.is_archived == False,  # noqa: E712
            SiteProject.status.not_in(["failed"]),
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    f"Active project with same blueprint + seed + site already exists "
                    f"(status: {dup.status})"
                ),
                "existing_project_id": str(dup.id),
            },
        )

    new_p = SiteProject(
        name=name,
        blueprint_id=src.blueprint_id,
        site_id=site.id,
        seed_keyword=seed_keyword,
        country=country,
        language=language,
        author_id=author_id,
        seed_is_brand=seed_is_brand,
        status="pending",
        current_page_index=0,
        celery_task_id=None,
        build_zip_url=None,
        error_log=None,
        stopping_requested=False,
        is_archived=False,
        started_at=None,
        completed_at=None,
        logs=[],
        serp_config=getattr(src, "serp_config", None) or {},
        project_keywords=getattr(src, "project_keywords", None),
    )
    db.add(new_p)
    db.commit()
    db.refresh(new_p)

    return {
        "id": str(new_p.id),
        "status": "cloned",
        "message": "Project cloned. Use Start to queue generation.",
    }


@router.post("/{id}/start")
def start_project(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending projects can be started (current: {project.status})",
        )

    _ensure_worker_available()

    result = process_site_project.delay(str(project.id))
    project.celery_task_id = result.id
    db.commit()

    return {
        "msg": "Project queued",
        "project_id": str(project.id),
        "celery_task_id": result.id,
    }


@router.post("/{id}/unarchive")
def unarchive_project(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.is_archived = False
    db.commit()
    return {"msg": "Project restored from archive", "project_id": str(project.id), "is_archived": False}


@router.delete("/{id}")
def delete_project(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status in ("generating", "pending"):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a project that is pending or generating. Stop or wait until it finishes.",
        )
    db.query(Task).filter(Task.project_id == id).delete(synchronize_session=False)
    db.delete(project)
    db.commit()
    return {"msg": "Project deleted", "project_id": id}


@router.post("/{id}/retry-failed")
def retry_failed_project_pages(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    failed_tasks = db.query(Task).filter(Task.project_id == id, Task.status == "failed").all()
    if not failed_tasks:
        raise HTTPException(status_code=400, detail="No failed tasks to retry")
    for t in failed_tasks:
        t.status = "pending"
        t.error_log = None
    project.status = "generating"
    project.stopping_requested = False
    project.completed_at = None
    db.commit()
    process_site_project.delay(str(project.id))
    return {
        "msg": "Failed pages reset to pending; project run queued",
        "project_id": str(project.id),
        "retried_count": len(failed_tasks),
    }


@router.post("/{id}/stop")
def stop_project(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.status not in ("pending", "generating"):
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot stop project in status '{project.status}'. "
                   f"Only 'pending' or 'generating' can be stopped."
        )
    
    project.stopping_requested = True
    db.commit()
    
    return {
        "msg": "Stop requested. Project will stop after current task completes.",
        "project_id": str(project.id),
        "status": project.status
    }

@router.post("/{id}/resume")
def resume_project(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.status != "stopped":
        raise HTTPException(status_code=400, detail="Can only resume stopped projects")

    project.status = "generating"
    project.stopping_requested = False
    project.completed_at = None
    db.commit()
    
    # Resume from where we left off
    process_site_project.delay(str(project.id))
    
    return {"msg": "Project resumed", "project_id": str(project.id)}

@router.post("/{id}/approve-page")
def approve_page(id: str, db: Session = Depends(get_db)):
    """Approve latest completed page and continue project generation."""
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != "awaiting_page_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Project is not awaiting approval (status: {project.status})",
        )

    project.status = "generating"
    logs = list(project.logs or [])
    logs.append({"ts": datetime.utcnow().isoformat() + "Z", "msg": "Page approved. Continuing generation.", "level": "info"})
    project.logs = logs
    db.commit()

    advance_project.delay(str(project.id), True)
    return {"msg": "Page approved, generation resumed", "project_id": str(project.id)}

@router.post("/{id}/rebuild-zip")
def rebuild_project_zip(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail="Project must be completed or failed to rebuild ZIP",
        )

    from app.services.site_builder import build_site

    try:
        zip_path = build_site(db, str(project.id))
        return {"msg": "ZIP rebuilt successfully", "zip_path": zip_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}/download")
def download_project_zip(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if not project.build_zip_url or not os.path.exists(project.build_zip_url):
        raise HTTPException(status_code=404, detail="ZIP file not found or not built yet")
        
    return FileResponse(project.build_zip_url, media_type="application/zip", filename=os.path.basename(project.build_zip_url))
