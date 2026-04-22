"""
Cluster additional project keywords across blueprint pages via a single LLM call.
"""

import json
from typing import Any

from app.config import settings
from app.services.llm import generate_text


def cluster_keywords(
    keywords: list[str],
    pages: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Returns clustered preview dict (not persisted).
    """
    pages_description = "\n".join(
        [
            f'- slug: "{p["slug"]}" | title: "{p["title"]}" | keyword: "{p.get("keyword_template", "")}" | type: {p.get("page_type", "")}'
            for p in pages
        ]
    )

    keywords_list = "\n".join([f"- {kw}" for kw in keywords])

    system_prompt = """You are an SEO keyword clustering expert.
Your task is to assign additional keywords to the most relevant pages of a website.

Rules:
1. Each keyword should be assigned to exactly ONE page (the most relevant one)
2. A keyword can be left unassigned if no page is a good fit
3. Consider semantic relevance, search intent, and topical proximity
4. A page can have 0 to many keywords assigned
5. Respond ONLY with valid JSON, no markdown wrapping"""

    user_prompt = f"""Website pages:
{pages_description}

Additional keywords to distribute:
{keywords_list}

Assign each keyword to the most relevant page. Respond with this exact JSON structure:
{{
  "assignments": {{
    "page_slug_1": ["keyword1", "keyword2"],
    "page_slug_2": ["keyword3"]
  }},
  "unassigned": ["keyword that doesn't fit any page"]
}}

Use exact page slugs and exact keywords from the lists above. Every keyword must appear exactly once — either in assignments or in unassigned."""

    model = settings.CLUSTERING_MODEL

    response, cost, actual_model, _usage = generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        max_tokens=4000,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        cleaned = response.strip().strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)

    assignments = parsed.get("assignments") or {}
    if not isinstance(assignments, dict):
        assignments = {}

    unassigned = parsed.get("unassigned") or []
    if not isinstance(unassigned, list):
        unassigned = []

    pages_by_slug = {p["slug"]: p for p in pages}
    clustered: dict[str, Any] = {}
    total_assigned = 0

    for slug, assigned_kws in assignments.items():
        if not isinstance(assigned_kws, list):
            continue
        page_info = pages_by_slug.get(slug, {})
        clustered[slug] = {
            "page_title": page_info.get("title", slug),
            "keyword": page_info.get("keyword_template", ""),
            "assigned_keywords": [str(x).strip() for x in assigned_kws if str(x).strip()],
        }
        total_assigned += len(clustered[slug]["assigned_keywords"])

    for p in pages:
        slug = p["slug"]
        if slug not in clustered:
            clustered[slug] = {
                "page_title": p.get("title", slug),
                "keyword": p.get("keyword_template", ""),
                "assigned_keywords": [],
            }

    return {
        "clustered": clustered,
        "unassigned": [str(x).strip() for x in unassigned if str(x).strip()],
        "total_keywords": len(keywords),
        "total_assigned": total_assigned,
        "cost": cost,
        "model": actual_model,
    }
