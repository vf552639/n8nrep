import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class Template(Base):
    """Reusable HTML shell for sites (not tied to a single site)."""

    __tablename__ = "templates"

    sites = relationship("Site", back_populates="template")

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    html_template = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    preview_screenshot = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class LegalPageTemplate(Base):
    """GEO-scoped legal page sample for LLM generation."""

    __tablename__ = "legal_page_templates"
    __table_args__ = (
        UniqueConstraint("country", "page_type", name="uq_legal_page_templates_country_page_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country = Column(String(10), nullable=False)
    page_type = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    html_content = Column(Text, nullable=False)
    variables = Column(JSONB, nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


LEGAL_PAGE_TYPES = (
    "privacy_policy",
    "terms_and_conditions",
    "cookie_policy",
    "responsible_gambling",
    "about_us",
)
