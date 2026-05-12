from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.prompt import Prompt
from app.models.prompt_preset import PromptPresetItem
from app.services.pipeline.errors import LLMError


def resolve_prompt_for_agent(
    db: Session, *, agent_name: str, preset_id: UUID | None
) -> Prompt:
    if preset_id is not None:
        item = (
            db.query(PromptPresetItem)
            .filter(
                PromptPresetItem.preset_id == preset_id,
                PromptPresetItem.agent_name == agent_name,
            )
            .first()
        )
        if item:
            prompt = db.query(Prompt).filter(Prompt.id == item.prompt_id).first()
            if prompt:
                return prompt

    prompt = (
        db.query(Prompt)
        .filter(Prompt.agent_name == agent_name, Prompt.is_active.is_(True))
        .first()
    )
    if not prompt and agent_name == "content_fact_checking":
        prompt = (
            db.query(Prompt)
            .filter(Prompt.agent_name == "fact_checking", Prompt.is_active.is_(True))
            .first()
        )
    if not prompt:
        raise LLMError(f"No active prompt found for agent: {agent_name}")
    return prompt
