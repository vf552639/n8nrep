from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import os
import dotenv

router = APIRouter()

def get_env_path():
    # Simple relative path to .env in project root
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

class SettingsUpdate(BaseModel):
    OPENROUTER_API_KEY: str = None
    DATAFORSEO_LOGIN: str = None
    DATAFORSEO_PASSWORD: str = None
    SERPAPI_KEY: str = None
    SERPER_API_KEY: str = None
    TELEGRAM_BOT_TOKEN: str = None
    TELEGRAM_CHAT_ID: str = None
    CELERY_CONCURRENCY: str = None
    EXCLUDE_WORDS: str = None
    SEQUENTIAL_MODE: str = None

@router.get("/")
def get_settings() -> Dict[str, Any]:
    """
    Returns non-critical settings for UI. 
    Masks passwords/keys partially if needed, but for an admin panel we might just return them or hide entirely.
    """
    path = get_env_path()
    if not os.path.exists(path):
        return {}
        
    env_vars = dotenv.dotenv_values(path)
    
    # Mask API keys for safety in GET response
    result = {}
    for k, v in env_vars.items():
        if "KEY" in k or "PASSWORD" in k or "TOKEN" in k:
            if v and len(v) > 8:
                result[k] = f"{v[:6]}...****{v[-4:]}"
            else:
                 result[k] = "***"
        else:
            result[k] = v
            
    return result

@router.put("/")
def update_settings(settings_in: SettingsUpdate):
    """
    Updates .env file natively. Requires app reload to fully take effect,
    unless reading config fresh everywhere. Fastapi restart might be needed 
    in production.
    """
    path = get_env_path()
    if not os.path.exists(path):
         raise HTTPException(status_code=404, detail=".env file not found")
         
    for key, value in settings_in.model_dump(exclude_unset=True).items():
        if value is not None and value != "***" and "..." not in value:
            dotenv.set_key(path, key, value)
            
    return {"msg": "Settings updated in .env (Restart maybe required)"}
