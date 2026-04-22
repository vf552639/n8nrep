from fastapi import Header, HTTPException

from app.config import settings


async def verify_api_key(x_api_key: str = Header(None)):
    if not settings.API_KEY:
        # If API_KEY is not configured in .env, disable authentication
        return

    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key (X-API-Key header)")
