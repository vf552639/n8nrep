import asyncio
import json
import logging
import time as time_module
import traceback
from datetime import datetime, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.database import SessionLocal
from app.services import event_bus

logger = logging.getLogger(__name__)

_running: dict = {}
_semaphore = None

_RETRYABLE_INFRA = (OperationalError, DBAPIError)


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        concurrency = int(getattr(settings, "CELERY_CONCURRENCY", 2) or 2)
        _semaphore = asyncio.Semaphore(concurrency)
    return _semaphore


# ── public async API ──────────────────────────────────────────────────────────

async def launch_project(project_id: str) -> None:
    """Create an asyncio background task for project execution. Idempotent."""
    if project_id in _running:
        return
    task = asyncio.create_task(_run_project_async(project_id))
    _running[project_id] = task
    task.add_done_callback(lambda _: _running.pop(project_id, None))


async def run_task(task_id: str) -> None:
    """Launch a single pipeline task in the background."""
    loop = asyncio.get_running_loop()
    asyncio.create_task(
        asyncio.wait_for(
            loop.run_in_executor(None, _task_sync, task_id),
            timeout=float(getattr(settings, "CELERY_TASK_TIME_LIMIT", 7200)),
        )
    )


def get_runner_status() -> dict:
    return {
        "status": "ok",
        "active_projects": len(_running),
        "running_ids": list(_running.keys()),
    }


async def start_cleanup_loop() -> None:
    """Background loop replacing Celery Beat cleanup_stale_tasks (runs every 10 min)."""
    while True:
        await asyncio.sleep(600)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _cleanup_stale_sync)


# ── async → sync bridge ───────────────────────────────────────────────────────

async def _run_project_async(project_id: str) -> None:
    loop = asyncio.get_running_loop()
    async with _get_semaphore():
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, _project_sync, project_id),
                timeout=float(getattr(settings, "CELERY_TASK_TIME_LIMIT", 7200)),
            )
        except asyncio.TimeoutError:
            logger.error("Project %s timed out", project_id)
            _mark_project_failed_sync(project_id, "Project timed out")
        except Exception as exc:
            logger.exception("Project %s crashed: %s", project_id, exc)
            _mark_project_failed_sync(project_id, str(exc))


# ── sync helpers ──────────────────────────────────────────────────────────────

def _append_project_log(db, project, msg: str, level: str = "info") -> None:
    logs = list(project.log_events or [])
    entry = {"ts": datetime.utcnow().isoformat() + "Z", "msg": msg, "level": level}
    logs.append(entry)
    project.log_events = logs[-500:]
    flag_modified(project, "log_events")
    event_bus.publish(f"project:{project.id}", entry)


def _load_failed_pages(project) -> list:
    if not project.error_log:
        return []
    try:
        data = json.loads(project.error_log)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_failed_page(project, failed_page: dict) -> None:
    pages = _load_failed_pages(project)
    pages.append(failed_page)
    project.error_log = json.dumps(pages, ensure_ascii=False)


def _merge_additional_keywords(existing, new_list: list) -> str:
    parts = []
    seen = set()
    for x in (existing or "").split(","):
        t = x.strip()
        if t and t.lower() not in seen:
            parts.append(t)
            seen.add(t.lower())
    for k in new_list:
        kl = k.strip()
        if kl and kl.lower() not in seen:
            parts.append(kl)
            seen.add(kl.lower())
    return ", ".join(parts)


def _fmt_duration(seconds: float) -> str:
    s = round(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _mark_project_failed_sync(project_id: str, msg: str) -> None:
    from app.models.project import SiteProject

    with SessionLocal() as db:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if project:
            project.status = "failed"
            project.error_log = msg
            project.completed_at = datetime.utcnow()
            _append_project_log(db, project, f"Project failed: {msg}", level="error")
            db.commit()


def _finalize_project(db, project_id: str) -> None:
    from app.models.blueprint import BlueprintPage
    from app.models.project import SiteProject
    from app.models.task import Task
    from app.services.site_builder import build_site

    project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
    if not project:
        return

    pages = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.blueprint_id == project.blueprint_id)
        .order_by(BlueprintPage.sort_order)
        .all()
    )
    n_pages = len(pages)
    project.current_page_index = n_pages
    if project.started_at is None:
        project.started_at = datetime.utcnow()

    build_site(db, project_id)

    all_tasks = db.query(Task).filter(Task.project_id == project.id).all()
    total_cost = float(sum((t.total_cost or 0) for t in all_tasks))
    ok = sum(1 for t in all_tasks if t.status == "completed")
    fail_n = sum(1 for t in all_tasks if t.status == "failed")

    project.status = "completed"
    if not _load_failed_pages(project):
        project.error_log = None
    project.completed_at = datetime.utcnow()
    _append_project_log(
        db,
        project,
        f"Project completed: {ok}/{n_pages} pages successful, {fail_n} failed. Total cost: ${total_cost:.4f}",
    )
    db.commit()
    event_bus.publish(f"project:{project_id}", {"type": "done", "status": "completed"})


def _run_page_sync(db, project_id: str, project, page, page_index: int, n_pages: int) -> None:
    from app.models.task import Task
    from app.services.pipeline import run_pipeline

    template = page.keyword_template
    if getattr(project, "seed_is_brand", False) and getattr(page, "keyword_template_brand", None):
        template = page.keyword_template_brand
    keyword = template.replace("{seed}", project.seed_keyword)
    proj_serp = getattr(project, "serp_config", None) or {}

    existing_task = (
        db.query(Task)
        .filter(
            Task.project_id == project.id,
            Task.blueprint_page_id == page.id,
            Task.status.in_(["pending", "failed"]),
        )
        .first()
    )
    if existing_task:
        project_task = existing_task
        project_task.status = "pending"
        project_task.error_log = None
        project_task.serp_config = proj_serp
        db.commit()
    else:
        project_task = Task(
            main_keyword=keyword,
            country=project.country,
            language=project.language,
            page_type=page.page_type,
            target_site_id=project.site_id,
            author_id=project.author_id,
            project_id=project.id,
            blueprint_page_id=page.id,
            status="pending",
            serp_config=proj_serp,
        )
        db.add(project_task)
        db.commit()
        db.refresh(project_task)

    db.refresh(project)
    pk_data = getattr(project, "project_keywords", None) or {}
    clustered_data = pk_data.get("clustered") if isinstance(pk_data, dict) else {}
    page_cluster = clustered_data.get(page.page_slug, {}) if isinstance(clustered_data, dict) else {}
    assigned = page_cluster.get("assigned_keywords") if isinstance(page_cluster, dict) else []
    if isinstance(assigned, list) and assigned:
        clustered_kws = [str(x).strip() for x in assigned if str(x).strip()]
        merged = _merge_additional_keywords(project_task.additional_keywords, clustered_kws)
        if merged != (project_task.additional_keywords or ""):
            project_task.additional_keywords = merged
            db.commit()
            db.refresh(project_task)

    _append_project_log(db, project, f"Starting page {page_index + 1}/{n_pages}: '{page.page_title}'")
    db.commit()

    t0 = time_module.monotonic()
    try:
        run_pipeline(db, str(project_task.id), auto_mode=True)
    except _RETRYABLE_INFRA as infra_err:
        db.rollback()
        db.refresh(project)
        db.refresh(project_task)
        tb = traceback.format_exc()
        if project_task.status not in ("failed", "completed"):
            project_task.status = "pending"
            project_task.error_log = tb[-8000:]
        _append_project_log(
            db, project,
            f"Infra error on page {page_index + 1}/{n_pages} ({type(infra_err).__name__}). Will retry next pass.",
            level="error",
        )
        db.commit()
        return
    except Exception:
        tb = traceback.format_exc()
        try:
            db.rollback()
        except Exception:
            pass
        db.refresh(project_task)
        if project_task.status not in ("failed", "completed"):
            project_task.status = "failed"
            project_task.error_log = tb[-8000:]
            db.commit()

    db.refresh(project_task)
    db.refresh(project)
    elapsed = time_module.monotonic() - t0

    if project_task.status == "completed":
        cost = float(project_task.total_cost or 0)
        _append_project_log(
            db, project,
            f"Page {page_index + 1}/{n_pages} completed in {_fmt_duration(elapsed)} (cost: ${cost:.4f})",
        )
        project.current_page_index = page_index + 1
        db.commit()
    else:
        error_detail = (project_task.error_log or "Unknown error").strip().split("\n", 1)[0][:500]
        _append_project_log(
            db, project,
            f"Page {page_index + 1}/{n_pages} FAILED: {error_detail} (task_id={project_task.id}). Skipping.",
            level="error",
        )
        _save_failed_page(project, {
            "page": page.page_title,
            "keyword": keyword,
            "task_id": str(project_task.id),
            "task_status": str(project_task.status),
            "error": error_detail,
        })
        project.current_page_index = page_index + 1
        db.commit()


def _project_sync(project_id: str) -> None:
    """Sync project runner. Runs in thread pool via run_in_executor."""
    from app.models.blueprint import BlueprintPage
    from app.models.project import SiteProject
    from app.models.task import Task

    with SessionLocal() as db:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if not project:
            logger.error("Project %s not found", project_id)
            return

        project.status = "generating"
        if getattr(project, "generation_started_at", None) is None:
            project.generation_started_at = datetime.utcnow()
        if project.started_at is None:
            project.started_at = datetime.utcnow()
        project.completed_at = None
        _append_project_log(db, project, "Project started. Launching page-by-page generation.")
        db.commit()

        pages = (
            db.query(BlueprintPage)
            .filter(BlueprintPage.blueprint_id == project.blueprint_id)
            .order_by(BlueprintPage.sort_order)
            .all()
        )
        n_pages = len(pages)

        for idx in range(n_pages):
            db.refresh(project)
            if project.stopping_requested:
                project.status = "stopped"
                project.stopping_requested = False
                project.completed_at = datetime.utcnow()
                _append_project_log(db, project, "Project stopped by user.", level="warning")
                db.commit()
                event_bus.publish(f"project:{project_id}", {"type": "done", "status": "stopped"})
                return

            page = pages[idx]
            done_task = (
                db.query(Task)
                .filter(
                    Task.project_id == project.id,
                    Task.blueprint_page_id == page.id,
                    Task.status == "completed",
                )
                .first()
            )
            if done_task:
                continue

            project.status = "generating"
            db.commit()

            try:
                _run_page_sync(db, project_id, project, page, idx, n_pages)
            except Exception as exc:
                logger.exception("Unhandled error on page %d: %s", idx, exc)
                project.status = "failed"
                project.error_log = traceback.format_exc()
                project.completed_at = datetime.utcnow()
                _append_project_log(db, project, f"Project failed: {exc!s}", level="error")
                db.commit()
                event_bus.publish(f"project:{project_id}", {"type": "done", "status": "failed"})
                return

        _finalize_project(db, project_id)


def _task_sync(task_id: str) -> None:
    """Single-task pipeline runner."""
    from app.services.pipeline import run_pipeline

    with SessionLocal() as db:
        try:
            run_pipeline(db, task_id)
        except Exception as exc:
            from app.models.task import Task
            task = db.query(Task).filter(Task.id == task_id).first()
            if task and task.status not in ("failed", "completed"):
                task.status = "failed"
                task.error_log = traceback.format_exc()
                db.commit()
            logger.exception("Single task %s failed: %s", task_id, exc)


def _cleanup_stale_sync() -> None:
    """Replaces Celery Beat cleanup_stale_tasks. Called every 10 min from start_cleanup_loop."""
    from app.models.task import Task

    stale_minutes = int(getattr(settings, "STALE_TASK_TIMEOUT_MINUTES", 15))
    threshold = datetime.utcnow() - timedelta(minutes=stale_minutes)
    with SessionLocal() as db:
        stale = (
            db.query(Task)
            .filter(
                Task.status == "processing",
                or_(
                    Task.last_heartbeat < threshold,
                    and_(Task.last_heartbeat.is_(None), Task.updated_at < threshold),
                ),
            )
            .all()
        )
        for t in stale:
            t.status = "stale"
            t.error_log = "Task timed out (no heartbeat). Cleaned up by desktop cleanup loop."
        if stale:
            db.commit()
            logger.info("Cleaned up %d stale task(s)", len(stale))
