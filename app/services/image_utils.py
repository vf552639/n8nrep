"""
Utility to extract MULTIMEDIA blocks from Final Structure Analysis JSON outline.
"""

def extract_multimedia_blocks(outline_json) -> list:
    """
    Recursively walks the JSON outline (result of final_structure_analysis)
    and collects all objects containing a multimedia key
    ("MULTIMEDIA"/"multimedia" and numbered variants).

    Returns a list of dicts:
    [
        {
            "id": "img_1",
            "section": "Introduction",
            "section_content": "First 300 chars of Content field...",
            "multimedia": { "Type": "...", "Description": "...", ... }
        },
        ...
    ]
    """
    blocks = []
    counter = 0

    def _walk(obj, parent_key="root"):
        nonlocal counter
        if isinstance(obj, dict):
            mm_keys = [
                k
                for k in obj.keys()
                if isinstance(k, str)
                and (k.upper() == "MULTIMEDIA" or k.upper().startswith("MULTIMEDIA_"))
            ]
            for mm_key in mm_keys:
                counter += 1
                blocks.append({
                    "id": f"img_{counter}",
                    "section": parent_key,
                    "section_content": str(obj.get("Content", "") or obj.get("content", ""))[:300],
                    "multimedia": obj[mm_key]
                })
            for key, value in obj.items():
                key_up = str(key).upper()
                if not (key_up == "MULTIMEDIA" or key_up.startswith("MULTIMEDIA_")):
                    _walk(value, parent_key=key)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item, parent_key=parent_key)

    if outline_json:
        _walk(outline_json)
    return blocks
