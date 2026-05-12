from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.prompt_preset import PromptPreset, PromptPresetItem
from app.schemas.prompt_preset import PromptPresetCreate, PromptPresetOut, PromptPresetUpdate

router = APIRouter()


@router.get("", response_model=list[PromptPresetOut])
def list_presets(db: Session = Depends(get_db)):
    return db.query(PromptPreset).order_by(PromptPreset.name).all()


@router.get("/{preset_id}", response_model=PromptPresetOut)
def get_preset(preset_id: UUID, db: Session = Depends(get_db)):
    p = db.query(PromptPreset).filter(PromptPreset.id == preset_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Preset not found")
    return p


@router.post("", response_model=PromptPresetOut, status_code=status.HTTP_201_CREATED)
def create_preset(payload: PromptPresetCreate, db: Session = Depends(get_db)):
    if db.query(PromptPreset).filter(PromptPreset.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Preset name already exists")

    if payload.is_default:
        db.query(PromptPreset).update({"is_default": False})

    preset = PromptPreset(
        name=payload.name,
        description=payload.description,
        is_default=payload.is_default,
    )
    db.add(preset)
    db.flush()
    for item in payload.items:
        db.add(
            PromptPresetItem(
                preset_id=preset.id,
                agent_name=item.agent_name,
                prompt_id=item.prompt_id,
            )
        )
    db.commit()
    db.refresh(preset)
    return preset


@router.put("/{preset_id}", response_model=PromptPresetOut)
def update_preset(preset_id: UUID, payload: PromptPresetUpdate, db: Session = Depends(get_db)):
    preset = db.query(PromptPreset).filter(PromptPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    if payload.is_default and not preset.is_default:
        db.query(PromptPreset).filter(PromptPreset.id != preset_id).update({"is_default": False})

    preset.name = payload.name
    preset.description = payload.description
    preset.is_default = payload.is_default

    db.query(PromptPresetItem).filter(PromptPresetItem.preset_id == preset_id).delete()
    for item in payload.items:
        db.add(
            PromptPresetItem(
                preset_id=preset.id,
                agent_name=item.agent_name,
                prompt_id=item.prompt_id,
            )
        )
    db.commit()
    db.refresh(preset)
    return preset


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(preset_id: UUID, db: Session = Depends(get_db)):
    preset = db.query(PromptPreset).filter(PromptPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    db.delete(preset)
    db.commit()
