from typing import Any

from pydantic import BaseModel


class PromptCreate(BaseModel):
    agent_name: str
    system_prompt: str
    user_prompt: str = ""
    model: str
    max_tokens: int | None = 2000
    temperature: float | None = 0.7
    frequency_penalty: float | None = 0.0
    presence_penalty: float | None = 0.0
    top_p: float | None = 1.0
    skip_in_pipeline: bool = False


class PromptUpdate(BaseModel):
    """In-place update of the existing prompt row (no new version)."""

    system_prompt: str
    user_prompt: str = ""
    model: str
    max_tokens: int | None = None
    max_tokens_enabled: bool = False
    temperature: float | None = 0.7
    temperature_enabled: bool = False
    frequency_penalty: float | None = 0.0
    frequency_penalty_enabled: bool = False
    presence_penalty: float | None = 0.0
    presence_penalty_enabled: bool = False
    top_p: float | None = 1.0
    top_p_enabled: bool = False
    skip_in_pipeline: bool = False


class PromptTest(BaseModel):
    system_prompt: str
    user_prompt: str
    test_data: str
    model: str
    max_tokens: int | None = None
    temperature: float | None = 0.7
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    top_p: float | None = None


class PromptTestContext(BaseModel):
    context: dict[str, Any]
    model: str | None = None
    max_tokens: int | None = None
    max_tokens_enabled: bool | None = None
    temperature: float | None = None
    temperature_enabled: bool | None = None
    frequency_penalty: float | None = None
    frequency_penalty_enabled: bool | None = None
    presence_penalty: float | None = None
    presence_penalty_enabled: bool | None = None
    top_p: float | None = None
    top_p_enabled: bool | None = None
