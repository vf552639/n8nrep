"""
Utility to extract MULTIMEDIA blocks from Final Structure Analysis JSON outline.
Supports multilingual keys and embedded multimedia markers in text fields.
"""

import re

# All variants of MULTIMEDIA-related JSON keys across supported languages
MULTIMEDIA_KEY_VARIANTS = {
    # English
    "multimedia",
    "multimedia_1",
    "multimedia_2",
    "multimedia_3",
    "multimedia_4",
    # Russian
    "мультимедиа",
    "мультимедиа_1",
    "мультимедиа_2",
    "мультимедиа_3",
    "медиа",
    "медиа_1",
    "медиа_2",
    "изображение",
    "изображение_1",
    "изображение_2",
    "картинка",
    "картинка_1",
    "картинка_2",
    # French
    "multimédia",
    "multimédia_1",
    "multimédia_2",
    "multimédia_3",
    "média",
    "média_1",
    "média_2",
    "médias",
    "médias_1",
    # German
    "medien",
    "medien_1",
    "medien_2",
    "multimedia_element",
    "multimedia_element_1",
    "bild",
    "bild_1",
    "bild_2",
    # Spanish
    "imagen",
    "imagen_1",
    "imagen_2",
    "medio",
    "medio_1",
    "medio_2",
    # Italian
    "immagine",
    "immagine_1",
    "immagine_2",
    # Polish
    "obraz",
    "obraz_1",
    "obraz_2",
    "grafika",
    "grafika_1",
    "grafika_2",
    # Portuguese
    "mídia",
    "mídia_1",
    "mídia_2",
    "imagem",
    "imagem_1",
    "imagem_2",
    # Generic / alternative English keys
    "image",
    "image_1",
    "image_2",
    "visual",
    "visual_1",
    "visual_2",
    "illustration",
    "illustration_1",
    "illustration_2",
    "media",
    "media_1",
    "media_2",
    "figure",
    "figure_1",
    "figure_2",
    "infographic",
    "infographic_1",
    "infographic_2",
    "image_description",
    "visual_element",
}


def _is_multimedia_key(key: str) -> bool:
    """True if JSON key is a multimedia-related key in any supported language."""
    if not isinstance(key, str):
        return False
    k = key.strip().lower()

    if k in MULTIMEDIA_KEY_VARIANTS:
        return True

    for base in ("multimedia", "мультимедиа", "multimédia", "medien", "média", "médias"):
        if k.startswith(base + "_"):
            return True

    return False


# Tag names for bracket / bold / dash patterns in free text
_MM_TEXT_TAGS = [
    "MULTIMEDIA",
    "IMAGE",
    "INFOGRAPHIC",
    "VISUAL",
    "МУЛЬТИМЕДИА",
    "ИЗОБРАЖЕНИЕ",
    "КАРТИНКА",
    "ИНФОГРАФИКА",
    "МЕДИА",
    "MULTIMÉDIA",
    "MÉDIA",
    "MÉDIAS",
    "INFOGRAPHIE",
    "MEDIEN",
    "BILD",
    "GRAFIK",
    "IMAGEN",
    "MEDIO",
    "INFOGRAFÍA",
    "IMMAGINE",
    "OBRAZ",
    "GRAFIKA",
]

_BRACKET_TAGS = "|".join(re.escape(tag) for tag in _MM_TEXT_TAGS)
_BRACKET_PATTERN = re.compile(
    rf"\[(?:{_BRACKET_TAGS})(?:_\d+)?\s*:\s*(.+?)\]",
    re.IGNORECASE | re.DOTALL,
)

_BOLD_PATTERN = re.compile(
    rf"\*\*(?:{_BRACKET_TAGS})(?:_\d+)?\*\*\s*[:—\-]\s*(.+?)(?:\n\n|\n(?=[A-Z#*\[])|$)",
    re.IGNORECASE | re.DOTALL,
)

_DASH_PATTERN = re.compile(
    rf"(?:^|\n)\s*(?:{_BRACKET_TAGS})(?:_\d+)?\s*[—\-:]+\s*(.+?)(?:\n|$)",
    re.IGNORECASE | re.MULTILINE,
)

_TYPE_NAMES = [
    "Image",
    "Infographic",
    "Infographie",
    "Infografía",
    "Изображение",
    "Инфографика",
    "Картинка",
    "Bild",
    "Grafik",
    "Immagine",
    "Imagen",
    "Obraz",
]
_TYPE_BRACKET_PATTERN = re.compile(
    rf'\[({"|".join(re.escape(t) for t in _TYPE_NAMES)})\s*:\s*(.+?)\]',
    re.IGNORECASE | re.DOTALL,
)


def _parse_multimedia_from_text(text: str) -> dict:
    """
    Parse free-form text into a multimedia dict (Type, Description, Purpose).
    """
    text = (text or "").strip()
    result = {"Type": "Image", "Description": text, "Purpose": ""}

    type_match = re.search(
        r"[Tt]ype\s*[:=]\s*(Image|Infographic|Infographie|Инфографика|Изображение|Bild|Imagen|Immagine)",
        text,
        re.IGNORECASE,
    )
    if type_match:
        result["Type"] = type_match.group(1).strip()
        text = text[: type_match.start()] + text[type_match.end() :]
    else:
        text_lower = text.lower()
        type_starters = {
            "infographic": "Infographic",
            "infographie": "Infographic",
            "инфографика": "Infographic",
            "infografía": "Infographic",
            "image": "Image",
            "изображение": "Image",
            "картинка": "Image",
            "bild": "Image",
            "imagen": "Image",
            "immagine": "Image",
            "obraz": "Image",
            "grafika": "Infographic",
            "tableau": "Image",
            "schéma": "Infographic",
            "схема": "Infographic",
        }
        for starter, mm_type in type_starters.items():
            if text_lower.startswith(starter):
                result["Type"] = mm_type
                text = text[len(starter) :].lstrip(" :—-–,.")
                break

    desc_match = re.search(
        r"[Dd]escription\s*[:=]\s*(.+?)(?:\.|,\s*[A-Z]|$)", text, re.DOTALL
    )
    if desc_match:
        result["Description"] = desc_match.group(1).strip()
    else:
        result["Description"] = re.sub(r"^[\s,\-—:]+", "", text).strip()

    purpose_match = re.search(r"[Pp]urpose\s*[:=]\s*(.+?)(?:\.|$)", text, re.DOTALL)
    if purpose_match:
        result["Purpose"] = purpose_match.group(1).strip()

    if not result["Description"]:
        result["Description"] = text[:200]

    return _ensure_default_multimedia_type(result)


def _extract_multimedia_from_text_content(text: str, parent_key: str) -> list:
    """
    Scan a string (e.g. Content) for embedded MULTIMEDIA markers in any supported language.
    """
    results = []
    seen_descriptions = set()

    def _add_result(parsed_mm: dict):
        desc_key = (parsed_mm.get("Description") or "")[:50]
        if desc_key and desc_key not in seen_descriptions:
            seen_descriptions.add(desc_key)
            results.append(
                {
                    "id": "",
                    "section": parent_key,
                    "section_content": text[:300],
                    "multimedia": parsed_mm,
                }
            )

    for match in _BRACKET_PATTERN.finditer(text):
        _add_result(_parse_multimedia_from_text(match.group(1)))

    for match in _BOLD_PATTERN.finditer(text):
        _add_result(_parse_multimedia_from_text(match.group(1).strip()))

    for match in _TYPE_BRACKET_PATTERN.finditer(text):
        mm_type = match.group(1).strip()
        desc = match.group(2).strip()
        _add_result(
            _ensure_default_multimedia_type(
                {
                    "Type": mm_type,
                    "Description": desc,
                    "Purpose": f"Visual element for '{parent_key}'",
                }
            )
        )

    for match in _DASH_PATTERN.finditer(text):
        desc_text = match.group(1).strip()
        if len(desc_text) > 10:
            _add_result(_parse_multimedia_from_text(desc_text))

    return results


def _ensure_default_multimedia_type(multimedia):
    """If Type/type is missing or blank, default to Image so pipeline does not skip blocks."""
    if not isinstance(multimedia, dict):
        return multimedia
    mm = dict(multimedia)
    t = (mm.get("Type") or mm.get("type") or "").strip()
    if not t:
        mm["Type"] = "Image"
    return mm


def extract_multimedia_blocks(outline_json) -> list:
    """
    Recursively walks the JSON outline (result of final_structure_analysis)
    and collects multimedia blocks (multilingual keys, string/list values, and text markers).

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
            mm_keys = [k for k in obj.keys() if _is_multimedia_key(k)]
            for mm_key in mm_keys:
                mm_val = obj[mm_key]
                section_content = str(
                    obj.get("Content", "") or obj.get("content", "")
                )[:300]

                if isinstance(mm_val, dict):
                    counter += 1
                    blocks.append(
                        {
                            "id": f"img_{counter}",
                            "section": parent_key,
                            "section_content": section_content,
                            "multimedia": _ensure_default_multimedia_type(mm_val),
                        }
                    )
                elif isinstance(mm_val, str) and len(mm_val.strip()) > 10:
                    counter += 1
                    blocks.append(
                        {
                            "id": f"img_{counter}",
                            "section": parent_key,
                            "section_content": section_content,
                            "multimedia": _parse_multimedia_from_text(mm_val),
                        }
                    )
                elif isinstance(mm_val, list):
                    for item in mm_val:
                        if isinstance(item, dict):
                            counter += 1
                            blocks.append(
                                {
                                    "id": f"img_{counter}",
                                    "section": parent_key,
                                    "section_content": section_content,
                                    "multimedia": _ensure_default_multimedia_type(
                                        item
                                    ),
                                }
                            )
                        elif isinstance(item, str) and len(item.strip()) > 10:
                            counter += 1
                            blocks.append(
                                {
                                    "id": f"img_{counter}",
                                    "section": parent_key,
                                    "section_content": section_content,
                                    "multimedia": _parse_multimedia_from_text(item),
                                }
                            )

            for key, value in obj.items():
                if _is_multimedia_key(key):
                    continue
                if isinstance(value, str) and len(value) > 30:
                    text_blocks = _extract_multimedia_from_text_content(
                        value, str(key)
                    )
                    for tb in text_blocks:
                        counter += 1
                        tb["id"] = f"img_{counter}"
                        blocks.append(tb)
                elif isinstance(value, (dict, list)):
                    _walk(value, parent_key=key)

        elif isinstance(obj, list):
            for item in obj:
                _walk(item, parent_key=parent_key)

    if outline_json:
        _walk(outline_json)
    return blocks
