from fastapi import APIRouter, Query, HTTPException
import os
import re

router = APIRouter()

LOG_FILE_PATH = "logs/app.log"
# Example match: 2024-03-20 12:00:00,000 - name - INFO - message
LOG_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?) - (.*?) - (INFO|WARNING|ERROR|DEBUG|CRITICAL) - (.*)$")

@router.get("/")
def get_recent_logs(lines: int = Query(200, ge=10, le=2000), level: str = Query("ALL")):
    if not os.path.exists(LOG_FILE_PATH):
        return {"logs": [{"timestamp": "", "level": "INFO", "service": "system", "message": "Log file not found or not created yet."}]}
        
    try:
        with open(LOG_FILE_PATH, "r") as f:
            all_lines = f.readlines()
            
            parsed_logs = []
            for line in all_lines:
                line_str = line.strip()
                if not line_str:
                    continue
                
                match = LOG_PATTERN.match(line_str)
                if match:
                    t, svc, lvl, msg = match.groups()
                    if level == "ALL" or level == lvl:
                        parsed_logs.append({
                            "timestamp": t,
                            "service": svc.strip(),
                            "level": lvl.strip(),
                            "message": msg.strip()
                        })
                else:
                    # If line doesn't match standard format, just append it as message with defaults
                    if level == "ALL":
                        parsed_logs.append({
                            "timestamp": "",
                            "service": "unknown",
                            "level": "INFO",
                            "message": line_str
                        })
            
            # Take last N lines
            recent_logs = parsed_logs[-lines:]
            
            # Return in mostly reverse chronological order 
            return {"logs": recent_logs[::-1]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")
