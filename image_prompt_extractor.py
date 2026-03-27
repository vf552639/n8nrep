"""Utilities for extracting and preparing image generation tasks.

This module parses article JSON, finds multimedia blocks, filters supported
types, and builds user prompts for image generation APIs.
"""

from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """You are a professional graphic designer specializing in web assets for iGaming and online casino review websites.

You will receive a task containing:
- TYPE: the kind of visual (Image or Infographic)
- DESCRIPTION: what the image should depict
- PURPOSE: how this image will be used on the page
- SECTION CONTEXT: the article section title this image belongs to

Your job is to generate a visually compelling image following these rules:

GENERAL RULES:
1. Output a single, self-contained image. No multi-panel compositions unless the type is "Infographic".
2. Landscape orientation, 16:9 aspect ratio.
3. Modern, clean, professional web design aesthetic.
4. Rich but not overwhelming color palette. Default to dark/neon theme (deep navy, electric blue, neon green accents) unless the description explicitly states otherwise.
5. NO real brand logos, trademarks, or copyrighted UI screenshots. Create abstract/stylized representations instead.
6. NO human faces or realistic human depictions (to avoid likeness and compliance issues).
7. NO text, words, letters, or numbers baked into the image. All text will be overlaid in HTML/CSS later. Exception: if the type is "Infographic", you may include SHORT labels (1-3 words per label, max 5 labels total) as part of the visual flow.

TYPE-SPECIFIC RULES:

If TYPE = "Image":
- Create a single hero-style visual or section illustration.
- Focus on atmosphere, mood, and thematic relevance to the section.
- Think editorial photography style but digitally composed — abstract casino elements (chips, cards, coins, dice) arranged artistically, glowing interfaces, futuristic dashboards.
- Depth of field and lighting effects encouraged.

If TYPE = "Infographic":
- Create a visual flowchart or step-by-step diagram.
- Use icons, arrows, numbered steps, and visual connectors.
- Keep the layout left-to-right or top-to-bottom, logical reading order.
- Short labels ARE allowed (e.g., "Step 1", "Sign Up", "Confirm").
- Flat design or isometric style preferred.
- Each step should be visually distinct (different icon/color).

WHAT TO AVOID:
- Photorealistic casino interiors (compliance risk)
- Real currency bills or coins with identifiable national symbols
- Anything that could be interpreted as promoting gambling to minors
- Cluttered compositions — whitespace is your friend
- Generic stock-photo aesthetic — aim for distinctive, editorial quality

QUALITY:
- Render at highest available resolution
- Sharp edges, no artifacts
- Consistent lighting and shadow direction

RESPONSE FORMAT (when producing structured output):
- Use JSON with keys: image_prompt (detailed English visual description for AI image models), alt_text, aspect_ratio.
- Do not embed aspect ratio or model flags inside the prompt text (no --ar, --v, etc.).
"""


GENERATABLE_TYPES = {"Image", "Infographic"}

TYPE_NORMALIZE_MAP = {
    # French variants
    "infographie": "Infographic",
    "infographie procedurale": "Infographic",
    "infographie procédurale": "Infographic",
    "tableau html": "Image",
    "tableau de donnees": "Image",
    "tableau de données": "Image",
    "tableau recapitulatif": "Image",
    "tableau récapitulatif": "Image",
    "tableau comparatif": "Image",
    "bouton d'action": "Image",
    "bouton d'action (cta)": "Image",
    "schema de processus": "Infographic",
    "schéma de processus": "Infographic",
    # English variants
    "infographic": "Infographic",
    "image": "Image",
    "chart": "Image",
    "table": "Image",
    "diagram": "Infographic",
}


def _normalize_type(value: Any) -> str:
    if value is None:
        return ""
    t_clean = str(value).strip().lower()
    return TYPE_NORMALIZE_MAP.get(t_clean, "")


def _safe_filename_part(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    cleaned = "".join(ch if ch in allowed else "_" for ch in value.strip().replace(" ", "_"))
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "item"


def extract_multimedia_blocks(article_json: dict[str, Any]) -> list[dict[str, str]]:
    """Recursively extract all objects that contain a `multimedia` key.

    Returns a normalized list of blocks:
    - type
    - description
    - purpose
    - location
    - parent_title
    """

    blocks: list[dict[str, str]] = []

    def walk(node: Any, current_parent_title: str = "") -> None:
        if isinstance(node, dict):
            parent_title = current_parent_title
            title_candidate = node.get("title")
            if isinstance(title_candidate, str) and title_candidate.strip():
                parent_title = title_candidate.strip()

            mm_keys = [k for k in node.keys() if isinstance(k, str) and (k.lower() == "multimedia" or k.lower().startswith("multimedia_"))]
            for mm_key in mm_keys:
                mm_raw = node.get(mm_key)
                if not isinstance(mm_raw, dict):
                    continue
                blocks.append(
                    {
                        "type": _normalize_type(mm_raw.get("type") or mm_raw.get("Type")),
                        "description": str(mm_raw.get("description") or mm_raw.get("Description") or "").strip(),
                        "purpose": str(mm_raw.get("purpose") or mm_raw.get("Purpose") or "").strip(),
                        "location": str(mm_raw.get("location") or mm_raw.get("Location") or "").strip(),
                        "parent_title": parent_title,
                    }
                )

            for value in node.values():
                walk(value, parent_title)
            return

        if isinstance(node, list):
            for item in node:
                walk(item, current_parent_title)

    walk(article_json)
    return blocks


def filter_generatable(blocks: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep only blocks that can be generated by the image pipeline."""

    return [b for b in blocks if _normalize_type(b.get("type")) in GENERATABLE_TYPES]


def build_image_prompt(block: dict[str, str]) -> str:
    """Build user prompt for a single multimedia block."""

    b_type = block.get("type", "").strip() or "Image"
    parent_title = block.get("parent_title", "").strip() or "Untitled Section"
    description = block.get("description", "").strip() or "Create a relevant visual for this section."
    purpose = block.get("purpose", "").strip() or "Support the section and improve readability."

    return f"""Create a {b_type} for a web article section.

Section title: "{parent_title}"

Visual description: {description}

This image serves the following purpose on the page: {purpose}

Additional context:
- This is for an online casino review website targeting Australian audience
- The site uses a dark theme with neon accent colors
- The image will be displayed as a full-width block between text sections
"""


def prepare_image_generation_tasks(article_json: dict[str, Any]) -> list[dict[str, str]]:
    """Parse article JSON and build image-generation task list."""

    blocks = extract_multimedia_blocks(article_json)
    blocks = filter_generatable(blocks)

    tasks: list[dict[str, str]] = []
    for index, block in enumerate(blocks, start=1):
        location = (block.get("location", "") or "").strip() or f"section_{index}"
        b_type = (block.get("type", "") or "Image").strip() or "Image"
        prompt = build_image_prompt(block)
        filename_hint = f"{_safe_filename_part(location)}_{_safe_filename_part(b_type.lower())}.png"

        tasks.append(
            {
                "location": location,
                "type": b_type,
                "prompt": prompt,
                "system_prompt": SYSTEM_PROMPT,
                "filename_hint": filename_hint,
            }
        )

    return tasks


if __name__ == "__main__":
    demo_article = {
        "title": "Best Online Casinos in Australia",
        "sections": [
            {
                "title": "Top Picks Comparison",
                "multimedia": {
                    "type": "Infographic",
                    "description": "Comparison flow of top 5 casino options by payout speed and bonuses.",
                    "purpose": "Help users quickly compare options.",
                    "location": "comparison_block",
                },
            },
            {
                "title": "Security and Licensing",
                "content": [
                    {
                        "multimedia": {
                            "Type": "Image",
                            "Description": "Abstract secure dashboard with shield icons and neon accents.",
                            "Purpose": "Visual break between dense text paragraphs.",
                            "Location": "security_section",
                        }
                    }
                ],
            },
        ],
    }

    from pprint import pprint

    pprint(prepare_image_generation_tasks(demo_article))
