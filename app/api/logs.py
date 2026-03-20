from fastapi import APIRouter, Query, HTTPException
import os

router = APIRouter()

LOG_FILE_PATH = "logs/app.log"

@router.get("/")
def get_recent_logs(lines: int = Query(100, ge=10, le=1000), level: str = Query("ALL")):
    if not os.path.exists(LOG_FILE_PATH):
        return {"logs": ["Log file not found or not created yet."]}
        
    try:
        with open(LOG_FILE_PATH, "r") as f:
            # Read all lines
            all_lines = f.readlines()
            
            # Filter by level if specified
            if level != "ALL":
                filtered_lines = [line for line in all_lines if f"[{level}]" in line or level in line]
            else:
                filtered_lines = all_lines
                
            # Take last N lines
            recent_lines = filtered_lines[-lines:]
            
            return {"logs": [line.strip() for line in recent_lines]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")
