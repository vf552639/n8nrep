import datetime

from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.jsonb_adapter import append_log_event
from app.schemas.log_event import LogEvent, LogLevel


def save_step_result(
    db: Session,
    task: Task,
    step_name: str,
    result: str,
    model: str = None,
    status: str = "completed",
    cost: float = 0.0,
    variables_snapshot: dict = None,
    resolved_prompts: dict = None,
    exclude_words_violations: dict = None,
    input_word_count: int = None,
    output_word_count: int = None,
    word_count_warning: bool = None,
    word_loss_percentage: float = None,
):
    if task.step_results is None:
        task.step_results = {}

    now_iso = datetime.datetime.utcnow().isoformat()
    previous_step = (
        (task.step_results or {}).get(step_name, {}) if isinstance(task.step_results, dict) else {}
    )
    step_data = {
        "status": status,
        "result": result[:50000] if result else None,
        "timestamp": now_iso,
    }
    if status == "running":
        step_data["started_at"] = previous_step.get("started_at") or now_iso
    elif previous_step.get("started_at"):
        step_data["started_at"] = previous_step.get("started_at")
    if model:
        step_data["model"] = model
    if cost > 0:
        step_data["cost"] = cost
    if variables_snapshot:
        step_data["variables_snapshot"] = variables_snapshot
    if resolved_prompts:
        step_data["resolved_prompts"] = resolved_prompts
    if exclude_words_violations:
        step_data["exclude_words_violations"] = exclude_words_violations
    if input_word_count is not None:
        step_data["input_word_count"] = input_word_count
    if output_word_count is not None:
        step_data["output_word_count"] = output_word_count
    if word_count_warning is not None:
        step_data["word_count_warning"] = word_count_warning
    if word_loss_percentage is not None:
        step_data["word_loss_percentage"] = word_loss_percentage

    updated = dict(task.step_results)
    updated[step_name] = step_data
    task.step_results = updated
    task.last_heartbeat = datetime.datetime.utcnow()
    db.commit()


def mark_step_running(db: Session, task: Task, step_key: str, model_name: str = None):
    save_step_result(
        db,
        task,
        step_key,
        result=None,
        status="running",
        model=model_name,
    )


def add_log(db: Session, task: Task, msg: str, level: str = "info", step: str = None):
    event = LogEvent(
        ts=datetime.datetime.utcnow(),
        level=LogLevel(level),
        msg=msg,
        step=step,
    )
    task.log_events = append_log_event(task.log_events, event, max_len=500)
    db.commit()


def completed_step_body(task: Task, step_key: str) -> str:
    sr = task.step_results or {}
    block = sr.get(step_key, {})
    if not isinstance(block, dict):
        return ""
    st = block.get("status")
    if st not in ("completed", "completed_with_warnings"):
        return ""
    return str(block.get("result") or "").strip()


_completed_step_body = completed_step_body
