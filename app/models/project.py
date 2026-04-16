from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class SiteProject(Base):
    __tablename__ = "site_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    blueprint_id = Column(UUID(as_uuid=True), ForeignKey('site_blueprints.id'), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey('sites.id'), nullable=False)
    seed_keyword = Column(String(500), nullable=False)
    country = Column(String(10), nullable=False)
    language = Column(String(10), nullable=False)
    seed_is_brand = Column(Boolean, default=False)
    author_id = Column(BigInteger, ForeignKey('authors.id'), nullable=True)
    status = Column(String(50), default='pending', comment="pending | generating | awaiting_page_approval | completed | failed | stopped")
    current_page_index = Column(Integer, default=0)
    celery_task_id = Column(String(255), nullable=True, comment="Celery task ID для отладки")
    stopping_requested = Column(Boolean, default=False, server_default="false", comment="Флаг запроса остановки")
    build_zip_url = Column(Text, nullable=True)
    error_log = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False, server_default="false", comment="Архивный проект")
    started_at = Column(DateTime, nullable=True)
    generation_started_at = Column(DateTime, nullable=True, comment="Actual generation start time")
    completed_at = Column(DateTime, nullable=True)
    logs = Column(JSONB, nullable=True, default=list)
    serp_config = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="SERP config: search_engine, depth, device, os",
    )
    project_keywords = Column(
        JSONB,
        nullable=True,
        comment="Additional keywords pool + clustering: raw, clustered, unassigned, etc.",
    )
    legal_template_map = Column(
        JSONB,
        nullable=True,
        comment="Mapping page_type -> legal_page_template_id (UUID string)",
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    blueprint = relationship("SiteBlueprint", back_populates="projects")
    site = relationship("Site")
    author = relationship("Author")
    tasks = relationship("Task", back_populates="project")
