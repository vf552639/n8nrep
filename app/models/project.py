from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
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
    status = Column(String(50), default='pending')
    current_page_index = Column(Integer, default=0)
    build_zip_url = Column(Text, nullable=True)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    blueprint = relationship("SiteBlueprint", back_populates="projects")
    site = relationship("Site")
    author = relationship("Author")
    tasks = relationship("Task", back_populates="project")
