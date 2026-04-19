from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database import get_db
from app.schemas.prompt import PromptCreate, PromptTest, PromptTestContext, PromptUpdate
from app.models.prompt import Prompt
from app.services.llm import generate_text
from app.services.pipeline import apply_template_vars
from app.services.prompt_llm_kwargs import llm_sampling_kwargs_from_prompt

router = APIRouter()


def _sanitize(text: Optional[str]) -> str:
    if text is None:
        return ""
    return (
        text.replace("\u2028", "\n")
        .replace("\u2029", "\n\n")
        .replace("\u00a0", " ")
        .replace("\ufeff", "")
    )


@router.get("/")
def get_prompts(active_only: bool = Query(True), db: Session = Depends(get_db)):
    query = db.query(Prompt)
    if active_only:
        query = query.filter(Prompt.is_active == True)
    prompts = query.order_by(Prompt.agent_name, Prompt.version.desc()).all()
    return [{
        "id": str(p.id),
        "agent_name": p.agent_name,
        "version": p.version,
        "is_active": p.is_active,
        "skip_in_pipeline": p.skip_in_pipeline,
        "model": p.model,
        "updated_at": p.updated_at.isoformat()
    } for p in prompts]


@router.get("/{prompt_id}/versions", response_model=List[Dict[str, Any]])
def list_prompt_versions(prompt_id: str, db: Session = Depends(get_db)):
    """All prompt rows for the same agent (version history), newest first."""
    current = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not current:
        raise HTTPException(status_code=404, detail="Prompt not found")
    rows = (
        db.query(Prompt)
        .filter(Prompt.agent_name == current.agent_name)
        .order_by(Prompt.version.desc())
        .all()
    )
    return [
        {
            "id": str(p.id),
            "prompt_id": str(p.id),
            "version": p.version,
            "is_active": p.is_active,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in rows
    ]


@router.post("/{prompt_id}/versions/{source_prompt_id}/restore")
def restore_prompt_version(
    prompt_id: str, source_prompt_id: str, db: Session = Depends(get_db)
):
    """Create a new active version by copying content from another row of the same agent."""
    current = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    source = db.query(Prompt).filter(Prompt.id == source_prompt_id).first()
    if not current or not source:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if current.agent_name != source.agent_name:
        raise HTTPException(status_code=400, detail="Version belongs to a different agent")

    existing = (
        db.query(Prompt)
        .filter(Prompt.agent_name == current.agent_name)
        .order_by(Prompt.version.desc())
        .first()
    )
    next_version = (existing.version + 1) if existing else 1

    db.query(Prompt).filter(Prompt.agent_name == current.agent_name).update({"is_active": False})

    new_prompt = Prompt(
        agent_name=source.agent_name,
        version=next_version,
        is_active=True,
        skip_in_pipeline=source.skip_in_pipeline,
        system_prompt=_sanitize(source.system_prompt),
        user_prompt=_sanitize(source.user_prompt or ""),
        model=source.model,
        max_tokens=source.max_tokens,
        max_tokens_enabled=getattr(source, "max_tokens_enabled", False),
        temperature=source.temperature,
        temperature_enabled=getattr(source, "temperature_enabled", False),
        frequency_penalty=source.frequency_penalty,
        frequency_penalty_enabled=getattr(source, "frequency_penalty_enabled", False),
        presence_penalty=source.presence_penalty,
        presence_penalty_enabled=getattr(source, "presence_penalty_enabled", False),
        top_p=source.top_p,
        top_p_enabled=getattr(source, "top_p_enabled", False),
    )
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)
    return {"id": str(new_prompt.id), "version": next_version}


def _prompt_to_response(prompt: Prompt) -> Dict[str, Any]:
    return {
        "id": str(prompt.id),
        "agent_name": prompt.agent_name,
        "system_prompt": prompt.system_prompt,
        "user_prompt": prompt.user_prompt,
        "version": prompt.version,
        "is_active": prompt.is_active,
        "skip_in_pipeline": prompt.skip_in_pipeline,
        "model": prompt.model,
        "max_tokens": prompt.max_tokens,
        "max_tokens_enabled": bool(getattr(prompt, "max_tokens_enabled", False)),
        "temperature": prompt.temperature if prompt.temperature is not None else 0.7,
        "temperature_enabled": bool(getattr(prompt, "temperature_enabled", False)),
        "frequency_penalty": prompt.frequency_penalty if prompt.frequency_penalty is not None else 0.0,
        "frequency_penalty_enabled": bool(getattr(prompt, "frequency_penalty_enabled", False)),
        "presence_penalty": prompt.presence_penalty if prompt.presence_penalty is not None else 0.0,
        "presence_penalty_enabled": bool(getattr(prompt, "presence_penalty_enabled", False)),
        "top_p": prompt.top_p if prompt.top_p is not None else 1.0,
        "top_p_enabled": bool(getattr(prompt, "top_p_enabled", False)),
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
    }


@router.get("/{prompt_id}")
def get_prompt(prompt_id: str, db: Session = Depends(get_db)):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _prompt_to_response(prompt)


@router.put("/{prompt_id}")
def update_prompt_in_place(
    prompt_id: str, body: PromptUpdate, db: Session = Depends(get_db)
):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt.system_prompt = _sanitize(body.system_prompt)
    prompt.user_prompt = _sanitize(body.user_prompt or "")
    prompt.model = body.model
    prompt.max_tokens = body.max_tokens
    prompt.max_tokens_enabled = body.max_tokens_enabled
    prompt.temperature = body.temperature
    prompt.temperature_enabled = body.temperature_enabled
    prompt.frequency_penalty = body.frequency_penalty
    prompt.frequency_penalty_enabled = body.frequency_penalty_enabled
    prompt.presence_penalty = body.presence_penalty
    prompt.presence_penalty_enabled = body.presence_penalty_enabled
    prompt.top_p = body.top_p
    prompt.top_p_enabled = body.top_p_enabled
    prompt.skip_in_pipeline = body.skip_in_pipeline
    db.commit()
    db.refresh(prompt)
    return _prompt_to_response(prompt)


@router.post("/")
def create_prompt(prompt_in: PromptCreate, db: Session = Depends(get_db)):
    # Deactivate older prompts for this agent
    existing = db.query(Prompt).filter(Prompt.agent_name == prompt_in.agent_name).order_by(Prompt.version.desc()).first()
    next_version = (existing.version + 1) if existing else 1
    
    db.query(Prompt).filter(Prompt.agent_name == prompt_in.agent_name).update({"is_active": False})
    
    t_val = prompt_in.temperature if prompt_in.temperature is not None else 0.7
    f_val = prompt_in.frequency_penalty if prompt_in.frequency_penalty is not None else 0.0
    p_val = prompt_in.presence_penalty if prompt_in.presence_penalty is not None else 0.0
    tp_val = prompt_in.top_p if prompt_in.top_p is not None else 1.0
    new_prompt = Prompt(
        agent_name=prompt_in.agent_name,
        version=next_version,
        is_active=True,
        skip_in_pipeline=prompt_in.skip_in_pipeline,
        system_prompt=_sanitize(prompt_in.system_prompt),
        user_prompt=_sanitize(prompt_in.user_prompt),
        model=prompt_in.model,
        max_tokens=prompt_in.max_tokens,
        max_tokens_enabled=prompt_in.max_tokens is not None and prompt_in.max_tokens > 0,
        temperature=t_val,
        temperature_enabled=abs(float(t_val) - 0.7) > 0.0001,
        frequency_penalty=f_val,
        frequency_penalty_enabled=abs(float(f_val)) > 0.0001,
        presence_penalty=p_val,
        presence_penalty_enabled=abs(float(p_val)) > 0.0001,
        top_p=tp_val,
        top_p_enabled=abs(float(tp_val) - 1.0) > 0.0001,
    )
    db.add(new_prompt)
    db.commit()
    
    return {"id": str(new_prompt.id), "version": next_version}

@router.post("/test")
def test_prompt(test_in: PromptTest):
    """
    Dry run the prompt with raw text data.
    """
    try:
        text, cost, actual_model, usage = generate_text(
            system_prompt=test_in.system_prompt,
            user_prompt=f"{test_in.user_prompt}\n\n{test_in.test_data}" if test_in.user_prompt else test_in.test_data,
            model=test_in.model,
            max_tokens=test_in.max_tokens,
            temperature=test_in.temperature,
            frequency_penalty=test_in.frequency_penalty,
            presence_penalty=test_in.presence_penalty,
            top_p=test_in.top_p
        )
        return {"result": text, "cost": cost, "model_used": actual_model, "usage": usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{prompt_id}/test")
def test_prompt_by_id(prompt_id: str, test_ctx: PromptTestContext, db: Session = Depends(get_db)):
    """
    Dry run the prompt explicitly using an existing Prompt from the database with JSON context vars.
    """
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
        
    try:
        system_text, _ = apply_template_vars(prompt.system_prompt, test_ctx.context)
        user_text, _ = apply_template_vars(prompt.user_prompt or "", test_ctx.context)
        
        target_model = test_ctx.model if test_ctx.model else prompt.model

        sampling = llm_sampling_kwargs_from_prompt(
            prompt,
            max_tokens_enabled=test_ctx.max_tokens_enabled,
            max_tokens=test_ctx.max_tokens,
            temperature_enabled=test_ctx.temperature_enabled,
            temperature=test_ctx.temperature,
            frequency_penalty_enabled=test_ctx.frequency_penalty_enabled,
            frequency_penalty=test_ctx.frequency_penalty,
            presence_penalty_enabled=test_ctx.presence_penalty_enabled,
            presence_penalty=test_ctx.presence_penalty,
            top_p_enabled=test_ctx.top_p_enabled,
            top_p=test_ctx.top_p,
        )

        text, cost, actual_model, usage = generate_text(
            system_prompt=system_text,
            user_prompt=user_text,
            model=target_model,
            **sampling,
        )
        usage_out: Dict[str, Any] = {}
        if usage:
            usage_out = dict(usage)
        return {
            "output": text,
            "cost": cost,
            "model_used": actual_model,
            "usage": usage_out,
            "resolved_prompts": {
                "system_prompt": system_text,
                "user_prompt": user_text,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
