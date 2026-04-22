import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    skip_in_pipeline = Column(Boolean, default=False, nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=True)
    model = Column(String(100), nullable=False)
    max_tokens = Column(Integer, nullable=True)
    max_tokens_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    temperature = Column(Float, default=0.7)
    temperature_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    frequency_penalty = Column(Float, default=0.0)
    frequency_penalty_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    presence_penalty = Column(Float, default=0.0)
    presence_penalty_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    top_p = Column(Float, default=1.0)
    top_p_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
