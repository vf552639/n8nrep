from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
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
    temperature: Optional[float] = 0.7
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    top_p: Optional[float] = 1.0

class PromptTestContext(BaseModel):
    context: Dict[str, Any]
    model: Optional[str] = None

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
        "temperature": prompt.temperature,
        "frequency_penalty": prompt.frequency_penalty,
        "presence_penalty": prompt.presence_penalty,
        "top_p": prompt.top_p
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
        text, cost, actual_model = generate_text(
            system_prompt=test_in.system_prompt,
            user_prompt=f"{test_in.user_prompt}\n\n{test_in.test_data}" if test_in.user_prompt else test_in.test_data,
            model=test_in.model,
            temperature=test_in.temperature,
            frequency_penalty=test_in.frequency_penalty,
            presence_penalty=test_in.presence_penalty,
            top_p=test_in.top_p
        )
        return {"result": text, "cost": cost, "model_used": actual_model}
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
        
        text, cost, actual_model = generate_text(
            system_prompt=system_text,
            user_prompt=user_text,
            model=target_model,
            temperature=prompt.temperature,
            frequency_penalty=prompt.frequency_penalty,
            presence_penalty=prompt.presence_penalty,
            top_p=prompt.top_p
        )
        return {"output": text, "usage": {"cost": cost, "total_tokens": "?"}, "model_used": actual_model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
