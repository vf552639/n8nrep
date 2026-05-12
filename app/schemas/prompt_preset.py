from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator


class PromptPresetItemIn(BaseModel):
    agent_name: str
    prompt_id: UUID


class PromptPresetItemOut(PromptPresetItemIn):
    id: UUID


class PromptPresetBase(BaseModel):
    name: str
    description: str | None = None
    is_default: bool = False


class PromptPresetCreate(PromptPresetBase):
    items: list[PromptPresetItemIn]

    @model_validator(mode="after")
    def _no_duplicate_agents(self):
        seen = set()
        for item in self.items:
            if item.agent_name in seen:
                raise ValueError(f"Duplicate agent_name in preset: {item.agent_name}")
            seen.add(item.agent_name)
        return self


class PromptPresetUpdate(PromptPresetCreate):
    pass


class PromptPresetOut(PromptPresetBase):
    id: UUID
    items: list[PromptPresetItemOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
