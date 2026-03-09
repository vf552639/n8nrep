from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import tasks, articles, sites, authors, prompts, dashboard, settings_api, blueprints, projects
from app.database import engine, Base

# Create tables is intentionally removed here.
# The Supabase tables are managed via manual SQL and Alembic migrations.
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SEO Content Generator API",
    description="Backend API for automatically generating SEO-optimized articles via LLM agents",
    version="1.0.0"
)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production (e.g. Vercel domain)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])
app.include_router(sites.router, prefix="/api/sites", tags=["Sites"])
app.include_router(authors.router, prefix="/api/authors", tags=["Authors"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["Prompts"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(blueprints.router, prefix="/api/blueprints", tags=["Blueprints"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SEO Content Generator API is running"}
