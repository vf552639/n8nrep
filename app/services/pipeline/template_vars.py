"""Template context assembly for LLM steps.

This module enriches step context with author/site/legal data and
`result_*` variables from completed pipeline steps.
"""

import json

from app.config import settings
from app.models.author import Author
from app.models.project import SiteProject
from app.services.deduplication import ContentDeduplicator
from app.services.legal_reference import inject_legal_template_vars
from app.services.template_engine import get_template_for_reference


def setup_template_vars(ctx):
    author_style = ""
    imitation = ""
    year = ""
    face = ""
    target_audience = ""
    rhythms_style = ""
    author_name = ""
    author_exclude_words = ""

    if ctx.task.author_id:
        author = ctx.db.query(Author).filter(Author.id == ctx.task.author_id).first()
        if author:
            author_style = author.bio or ""
            imitation = author.imitation or ""
            year = author.year or ""
            face = author.face or ""
            target_audience = author.target_audience or ""
            rhythms_style = author.rhythms_style or ""
            author_name = author.author or ""
            author_exclude_words = author.exclude_words or ""

    combined_exclude = []
    if settings.EXCLUDE_WORDS:
        combined_exclude.append(settings.EXCLUDE_WORDS)
    if author_exclude_words:
        combined_exclude.append(author_exclude_words)
    final_exclude = ", ".join(combined_exclude)

    ctx.author_block = (
        f"Author Style/Text Block: {author_style}\n"
        f"Imitation (Mimicry): {imitation}\n"
        f"Year: {year}\n"
        f"Face: {face}\n"
        f"Target Audience: {target_audience}\n"
        f"Rhythms & Style: {rhythms_style}\n"
        f"Exclude Words: {final_exclude}"
    )
    already_covered_topics = ""
    if ctx.task.project_id:
        deduplicator = ContentDeduplicator(ctx.db)
        already_covered_topics = deduplicator.get_already_covered(ctx.task.project_id, ctx.task.id)

    ctx.template_vars = {
        "already_covered_topics": already_covered_topics,
        "keyword": ctx.task.main_keyword,
        "additional_keywords": ctx.task.additional_keywords
        or ctx.analysis_vars.get("additional_keywords", ""),
        "country": ctx.task.country,
        "language": ctx.task.language,
        "page_type": ctx.task.page_type,
        "competitors_headers": json.dumps(
            ctx.task.outline.get("scrape_info", {}).get("headers", []), ensure_ascii=False
        ),
        "merged_markdown": ctx.task.competitors_text or "",
        "avg_word_count": str(ctx.task.outline.get("scrape_info", {}).get("avg_words", 800)),
        "author": author_name,
        "author_style": author_style,
        "imitation": imitation,
        "target_audience": target_audience,
        "face": face,
        "year": year,
        "rhythms_style": rhythms_style,
        "exclude_words": final_exclude,
        "site_name": ctx.site_name,
        "result_ai_structure_analysis": ctx.task.outline.get("ai_structure", ""),
        "intent": ctx.task.outline.get("ai_structure_parsed", {}).get("intent", ""),
        "Taxonomy": ctx.task.outline.get("ai_structure_parsed", {}).get("Taxonomy", ""),
        "Attention": ctx.task.outline.get("ai_structure_parsed", {}).get("Attention", ""),
        "structura": ctx.task.outline.get("ai_structure_parsed", {}).get("structura", ""),
        "result_chunk_cluster_analysis": ctx.task.outline.get("chunk_analysis", ""),
        "result_competitor_structure_analysis": ctx.task.outline.get("competitor_structure", ""),
        "result_final_structure_analysis": ctx.task.outline.get(
            "final_structure", json.dumps(ctx.task.outline.get("final_outline", {}), ensure_ascii=False)
        ),
        "page_slug": ctx.page_slug,
        "page_title": ctx.page_title,
        "all_site_pages": json.dumps(ctx.all_site_pages, ensure_ascii=False),
        "competitor_titles": ctx.analysis_vars.get("competitor_titles", ""),
        "competitor_descriptions": ctx.analysis_vars.get("competitor_descriptions", ""),
        "highlighted_keywords": ctx.analysis_vars.get("highlighted_keywords", ""),
        "paa_with_answers": ctx.analysis_vars.get("paa_with_answers", ""),
        "featured_snippet": ctx.analysis_vars.get("featured_snippet", ""),
        "knowledge_graph": ctx.analysis_vars.get("knowledge_graph", ""),
        "ai_overview": ctx.analysis_vars.get("ai_overview", ""),
        "answer_box": ctx.analysis_vars.get("answer_box", ""),
        "serp_features": ctx.analysis_vars.get("serp_features", ""),
        "search_intent_signals": ctx.analysis_vars.get("search_intent_signals", ""),
        "related_searches": ctx.analysis_vars.get("related_searches", ""),
        "people_also_search": ctx.analysis_vars.get("people_also_search", ""),
        "structure_fact_checking": "",
    }

    sr = ctx.task.step_results or {}
    for step_key, step_data in sr.items():
        if step_key.startswith("_") or not isinstance(step_data, dict):
            continue
        if step_data.get("status") != "completed":
            continue
        raw_res = step_data.get("result")
        if raw_res is None:
            continue
        var_key = f"result_{step_key}"
        cur = ctx.template_vars.get(var_key)
        if cur is None or (isinstance(cur, str) and not str(cur).strip()):
            ctx.template_vars[var_key] = str(raw_res)

    use_template = True
    if ctx.task.project_id:
        project = ctx.db.query(SiteProject).filter(SiteProject.id == ctx.task.project_id).first()
        if project and not getattr(project, "use_site_template", True):
            use_template = False

    if use_template:
        site_template_html, site_template_name = get_template_for_reference(ctx.db, str(ctx.task.target_site_id))
        ctx.template_vars["site_template_html"] = site_template_html or ""
        ctx.template_vars["site_template_name"] = site_template_name or ""
    else:
        ctx.template_vars["site_template_html"] = ""
        ctx.template_vars["site_template_name"] = ""

    inject_legal_template_vars(ctx)

__all__ = ["setup_template_vars"]
