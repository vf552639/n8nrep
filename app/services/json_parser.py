import json
import re
from typing import Dict, Any

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Attempts to parse a JSON string even if it's wrapped in markdown formatting 
    (like ```json\n...\n```) or contains leading/trailing text.
    """
    if not text:
        return {}
        
    text = text.strip()
    
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # Remove markdown code block wrappers
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
        
    if text.endswith("```"):
        text = text[:-3]
        
    text = text.strip()
    
    # Try parsing again after stripping markdown
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # Last resort: Try to find the first '{' and last '}'
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
    # If all fails, return empty object so pipeline does not crash completely,
    # or raise an exception if you prefer strict failure.
    # In SEO Pipeline, returning empty dict is usually safer to let generation proceed with fallback text.
    return {}
