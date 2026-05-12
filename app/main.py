import asyncio
import logging
import os
import subprocess
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from starlette.exceptions import HTTPException

from app.api import (
    articles,
    authors,
    blueprints,
    dashboard,
    health,
    legal_pages,
    logs,
    projects,
    prompts,
    settings_api,
    sites,
    sse,
    tasks,
    templates,
)
from app.api.deps import verify_api_key
from app.config import settings
from app.logging_config import configure_logging

os.makedirs("logs", exist_ok=True)

configure_logging(
    json_logs=settings.LOG_JSON,
    level=settings.LOG_LEVEL,
    log_file_path="logs/app.log",
)
logger = logging.getLogger(__name__)


def _run_desktop_migrations() -> None:
    """Auto-apply desktop Alembic branch migrations at startup and ensure the DB dir exists."""
    # Ensure the SQLite DB directory exists before migration (mkdir was deferred from config validator)
    db_path = Path(settings.SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "desktop@head"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        logger.error("Alembic desktop migration failed:\n%s\n%s", result.stdout, result.stderr)
        raise RuntimeError("Database migration failed — cannot start")
    logger.info("Desktop migrations applied: %s", result.stdout.strip() or "up to date")


def verify_migrations() -> None:
    try:
        root = Path(__file__).resolve().parent.parent
        cfg = Config(str(root / "alembic.ini"))
        script = ScriptDirectory.from_config(cfg)
        head_rev = script.get_current_head()
        check_engine = create_engine(settings.SUPABASE_DB_URL)
        try:
            with check_engine.connect() as conn:
                db_rev = MigrationContext.configure(conn).get_current_revision()
        finally:
            check_engine.dispose()
        if db_rev != head_rev:
            banner = "=" * 70
            logger.error(
                "\n%s\n⚠  MIGRATION MISMATCH — app may 500 on requests touching new columns\n"
                "   DB revision:   %s\n"
                "   Alembic head:  %s\n"
                "   Fix: docker-compose exec web alembic upgrade head\n%s",
                banner,
                db_rev,
                head_rev,
                banner,
            )
        else:
            logger.info("Alembic migrations up to date: %s", head_rev)
    except Exception as e:
        logger.warning("Could not verify migration status: %s", e)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.AUTH_DISABLED:
        logger.warning(
            "AUTH_DISABLED is true: X-API-Key checks are disabled. Never enable this in production."
        )
    if settings.DESKTOP_MODE:
        _run_desktop_migrations()
        from app.services import event_bus as _event_bus
        _event_bus.init(asyncio.get_event_loop())
        from app.services.project_runner import start_cleanup_loop
        cleanup_task = asyncio.create_task(start_cleanup_loop())
    else:
        verify_migrations()
    yield
    if settings.DESKTOP_MODE:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="SEO Content Generator API",
    description="Backend API for automatically generating SEO-optimized articles via LLM agents",
    version="1.0.0",
    dependencies=[Depends(verify_api_key)],
    lifespan=lifespan,
)

_raw_cors = (settings.CORS_ORIGINS or "").strip()
origins = [o.strip() for o in _raw_cors.split(",") if o.strip()] if _raw_cors else ["*"]
# Browsers reject Access-Control-Allow-Origin: * with credentials; Starlette echoes request Origin
# when origins is ["*"], which effectively allows any origin with credentials — disable credentials
# whenever wildcard is used (task60).
_allow_credentials = True
if not origins or "*" in origins:
    _allow_credentials = False
    if not origins:
        origins = ["*"]

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Skip buffering middleware for SSE streaming endpoints to avoid blocking the response stream.
    if request.url.path.startswith("/api/sse"):
        return await call_next(request)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


# API Routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])
app.include_router(sites.router, prefix="/api/sites", tags=["Sites"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(legal_pages.router, prefix="/api/legal-pages", tags=["Legal Pages"])
app.include_router(authors.router, prefix="/api/authors", tags=["Authors"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["Prompts"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(blueprints.router, prefix="/api/blueprints", tags=["Blueprints"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(sse.router, prefix="/api/sse", tags=["SSE"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=dict(exc.headers) if exc.headers else None,
        )
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url.path,
        exc,
        tb,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {type(exc).__name__}: {str(exc)[:500]}",
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.get("/")
def read_root():
    return {"status": "ok", "message": "SEO Content Generator API is running"}
