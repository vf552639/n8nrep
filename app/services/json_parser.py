import json
import re
from typing import Dict, Any

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Attempts to parse a JSON string even if it's wrapped in markdown formatting 
    (like ```json\n...\n```) or contains leading/trailing text.
    Also handles cases where required keys are inside a nested object.
    """
    if not text:
        return {}
        
    # 1. Strip markdown fences and whitespace
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    
    # Try direct parse
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Warning: clean_and_parse_json failed: {e} | text[:200]={text[:200]}")
        return {}
        
    # 2. Check if required keys are at the top level, or nested inside the first dict
    required = {"intent", "Taxonomy", "Attention", "structura"}
    if isinstance(data, dict):
        if not required.intersection(data.keys()):
            # Try to find them in the first nested dict
            for v in data.values():
                if isinstance(v, dict) and required.intersection(v.keys()):
                    return v
        return data
        
    return {}
