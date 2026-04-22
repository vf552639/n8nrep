import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID

from app.database import Base

task_status_enum = ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    "stale",
    "paused",
    name="task_status",
)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    main_keyword = Column(String(500), nullable=False)
    country = Column(String(10), nullable=False)
    language = Column(String(10), nullable=False)
    page_type = Column(String(50), nullable=False, default="article")
    target_site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False, index=True)
    author_id = Column(BigInteger, ForeignKey("authors.id"), nullable=True)
    status = Column(task_status_enum, default="pending", nullable=False, index=True)
    total_cost = Column(Float, default=0.0)
    error_log = Column(Text, nullable=True)
    serp_data = Column(JSONB, nullable=True)
    competitors_text = Column(Text, nullable=True)
    outline = Column(JSONB, nullable=True)
    additional_keywords = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    step_results = Column(JSONB, nullable=True, default={})
    serp_config = Column(JSONB, nullable=True, default={})
    log_events = Column(JSONB, nullable=False, default=list, server_default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=True)

    project_id = Column(UUID(as_uuid=True), ForeignKey("site_projects.id"), nullable=True, index=True)
    blueprint_page_id = Column(UUID(as_uuid=True), ForeignKey("blueprint_pages.id"), nullable=True)

    from sqlalchemy.orm import relationship

    project = relationship("SiteProject", back_populates="tasks")
    blueprint_page = relationship("BlueprintPage")
