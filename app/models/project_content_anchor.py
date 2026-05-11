from datetime import datetime

import sqlalchemy as sa

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class ProjectContentAnchor(Base):
    __tablename__ = "project_content_anchors"

    id = Column(Integer, primary_key=True, index=True)  # SERIAL in SQL
    project_id = Column(
        sa.Uuid(as_uuid=True), ForeignKey("site_projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_id = Column(
        sa.Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    keyword = Column(String(500), nullable=True)
    title = Column(String(500), nullable=True)
    h2_headings = Column(sa.JSON, default=[])
    h3_headings = Column(sa.JSON, default=[])
    key_phrases = Column(sa.JSON, default=[])
    first_paragraphs = Column(sa.JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("SiteProject", foreign_keys=[project_id])
    task = relationship("Task", foreign_keys=[task_id])
