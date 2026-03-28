import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Boolean, Float
from app.database import Base

class GeneratedArticle(Base):
    __tablename__ = "generated_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id'), nullable=False)
    title = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    html_content = Column(Text, nullable=True)
    full_page_html = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    
    # Fact-checking fields
    fact_check_status = Column(String(20), default="") # "pass", "warn", "fail", ""
    fact_check_issues = Column(JSONB, default=[])
    fact_check_score = Column(Float, default=0.0)
    needs_review = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
