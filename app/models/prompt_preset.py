import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class PromptPreset(Base):
    __tablename__ = "prompt_presets"

    id = Column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, server_default="0", default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship(
        "PromptPresetItem",
        back_populates="preset",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class PromptPresetItem(Base):
    __tablename__ = "prompt_preset_items"
    __table_args__ = (UniqueConstraint("preset_id", "agent_name", name="uq_preset_agent"),)

    id = Column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    preset_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("prompt_presets.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_name = Column(String(100), nullable=False, index=True)
    prompt_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
    )

    preset = relationship("PromptPreset", back_populates="items")
