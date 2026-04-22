from sqlalchemy.orm import Session

from app.services import _pipeline_legacy as legacy


def get_prompt_obj(db: Session, agent_name: str):
    return legacy.get_prompt_obj(db, agent_name)


def call_agent(*args, **kwargs):
    return legacy.call_agent(*args, **kwargs)


def call_agent_with_exclude_validation(*args, **kwargs):
    return legacy.call_agent_with_exclude_validation(*args, **kwargs)
