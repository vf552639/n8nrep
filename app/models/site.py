import uuid
from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base

class Site(Base):
    __tablename__ = "sites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    domain = Column(String(200), nullable=False)
    country = Column(String(10), nullable=False)
    language = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)


class SiteTemplate(Base):
    __tablename__ = "site_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey('sites.id'), nullable=False)
    template_name = Column(String(200), nullable=False)
    html_template = Column(Text, nullable=False)
    pages_config = Column(JSONB, nullable=True)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
