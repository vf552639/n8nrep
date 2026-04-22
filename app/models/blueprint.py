import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SiteBlueprint(Base):
    __tablename__ = "site_blueprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pages = relationship("BlueprintPage", back_populates="blueprint", cascade="all, delete-orphan")
    projects = relationship("SiteProject", back_populates="blueprint")


class BlueprintPage(Base):
    __tablename__ = "blueprint_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blueprint_id = Column(
        UUID(as_uuid=True), ForeignKey("site_blueprints.id", ondelete="CASCADE"), nullable=False
    )
    page_slug = Column(String(100), nullable=False)
    page_title = Column(String(300), nullable=False)
    page_type = Column(String(50), nullable=False, default="article")
    keyword_template = Column(String(500), nullable=False)
    keyword_template_brand = Column(String(500), nullable=True)
    filename = Column(String(200), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    nav_label = Column(String(100), nullable=True)
    show_in_nav = Column(Boolean, default=True)
    show_in_footer = Column(Boolean, default=True)
    use_serp = Column(Boolean, default=True)
    pipeline_preset = Column(String(20), nullable=False, default="full")
    pipeline_steps_custom = Column(JSONB, nullable=True)
    default_legal_template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("legal_page_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    blueprint = relationship("SiteBlueprint", back_populates="pages")
