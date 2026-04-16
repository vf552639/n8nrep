import logging
import os
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
    tasks,
    templates,
)
from app.api.deps import verify_api_key
from app.config import settings

# Configure file logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", mode="a"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


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
    verify_migrations()
    yield


app = FastAPI(
    title="SEO Content Generator API",
    description="Backend API for automatically generating SEO-optimized articles via LLM agents",
    version="1.0.0",
    dependencies=[Depends(verify_api_key)],
    lifespan=lifespan,
)

origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")] if settings.CORS_ORIGINS else ["*"]

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
