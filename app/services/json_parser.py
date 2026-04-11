import json
import re
from typing import Any, Dict, Optional, Set


def clean_and_parse_json(
    text: str, unwrap_keys: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Parse JSON string, stripping markdown fences.
    If direct parse fails, extracts the first JSON object from the text (e.g. prose
    before/after, or trailing commentary after a valid object).

    If unwrap_keys is provided and the top-level dict does not contain any of those
    keys, walks nested dict values and returns the first nested dict that does
    (used for ai_structure_analysis wrappers).
    """
    if not text:
        return {}

    text = re.sub(r"```json\s*|\s*```", "", text).strip()

    data: Any = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start != -1:
            try:
                data, _ = json.JSONDecoder().raw_decode(text, start)
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]*\}", text)
                if match:
                    try:
                        data = json.loads(match.group())
                    except json.JSONDecodeError as e:
                        print(
                            f"Warning: clean_and_parse_json failed: {e} | text[:200]={text[:200]}"
                        )
                        return {}
                else:
                    print(
                        f"Warning: clean_and_parse_json no JSON found | text[:200]={text[:200]}"
                    )
                    return {}
        else:
            print(
                f"Warning: clean_and_parse_json no JSON found | text[:200]={text[:200]}"
            )
            return {}

    if not isinstance(data, dict):
        return {}

    if unwrap_keys:
        if not unwrap_keys.intersection(data.keys()):
            for v in data.values():
                if isinstance(v, dict) and unwrap_keys.intersection(v.keys()):
                    return v

    return data
