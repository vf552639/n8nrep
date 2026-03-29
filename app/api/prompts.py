from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.database import get_db
from app.models.prompt import Prompt
from app.services.llm import generate_text
from app.services.pipeline import apply_template_vars

router = APIRouter()

class PromptCreate(BaseModel):
    agent_name: str
    system_prompt: str
    user_prompt: str = ""
    model: str
    max_tokens: Optional[int] = 2000
    temperature: Optional[float] = 0.7
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    top_p: Optional[float] = 1.0
    skip_in_pipeline: bool = False

class PromptTest(BaseModel):
    system_prompt: str
    user_prompt: str
    test_data: str
    model: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    top_p: Optional[float] = 1.0

class PromptTestContext(BaseModel):
    context: Dict[str, Any]
    model: Optional[str] = None
    max_tokens: Optional[int] = None

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
        system_prompt=source.system_prompt,
        user_prompt=source.user_prompt or "",
        model=source.model,
        max_tokens=source.max_tokens,
        temperature=source.temperature,
        frequency_penalty=source.frequency_penalty,
        presence_penalty=source.presence_penalty,
        top_p=source.top_p,
    )
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)
    return {"id": str(new_prompt.id), "version": next_version}


@router.get("/{prompt_id}")
def get_prompt(prompt_id: str, db: Session = Depends(get_db)):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
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
        "temperature": prompt.temperature if prompt.temperature is not None else 0.7,
        "frequency_penalty": prompt.frequency_penalty if prompt.frequency_penalty is not None else 0.0,
        "presence_penalty": prompt.presence_penalty if prompt.presence_penalty is not None else 0.0,
        "top_p": prompt.top_p if prompt.top_p is not None else 1.0
    }

@router.post("/")
def create_prompt(prompt_in: PromptCreate, db: Session = Depends(get_db)):
    # Deactivate older prompts for this agent
    existing = db.query(Prompt).filter(Prompt.agent_name == prompt_in.agent_name).order_by(Prompt.version.desc()).first()
    next_version = (existing.version + 1) if existing else 1
    
    db.query(Prompt).filter(Prompt.agent_name == prompt_in.agent_name).update({"is_active": False})
    
    new_prompt = Prompt(
        agent_name=prompt_in.agent_name,
        version=next_version,
        is_active=True,
        skip_in_pipeline=prompt_in.skip_in_pipeline,
        system_prompt=prompt_in.system_prompt,
        user_prompt=prompt_in.user_prompt,
        model=prompt_in.model,
        max_tokens=prompt_in.max_tokens,
        temperature=prompt_in.temperature,
        frequency_penalty=prompt_in.frequency_penalty,
        presence_penalty=prompt_in.presence_penalty,
        top_p=prompt_in.top_p
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
        max_tokens = (
            test_ctx.max_tokens if test_ctx.max_tokens is not None else prompt.max_tokens
        )

        text, cost, actual_model, usage = generate_text(
            system_prompt=system_text,
            user_prompt=user_text,
            model=target_model,
            max_tokens=max_tokens,
            temperature=prompt.temperature,
            frequency_penalty=prompt.frequency_penalty,
            presence_penalty=prompt.presence_penalty,
            top_p=prompt.top_p
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
