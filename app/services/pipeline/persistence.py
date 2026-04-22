from sqlalchemy.orm import Session

from app.services import _pipeline_legacy as legacy


def save_step_result(*args, **kwargs):
    return legacy.save_step_result(*args, **kwargs)


def mark_step_running(db: Session, task, step_key: str, model_name: str = None):
    return legacy.mark_step_running(db, task, step_key, model_name=model_name)


def add_log(db: Session, task, msg: str, level: str = "info", step: str = None):
    return legacy.add_log(db, task, msg=msg, level=level, step=step)


def completed_step_body(task, step_key: str) -> str:
    return legacy._completed_step_body(task, step_key)
