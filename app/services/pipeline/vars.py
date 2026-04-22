import json
import re

from app.config import settings
from app.models.author import Author
from app.models.project import SiteProject
from app.services.deduplication import ContentDeduplicator
from app.services.legal_reference import inject_legal_template_vars
from app.services.pipeline_constants import (
    STEP_AI_ANALYSIS,
    STEP_CHUNK_ANALYSIS,
    STEP_COMP_STRUCTURE,
    STEP_FINAL_ANALYSIS,
    STEP_FINAL_EDIT,
    STEP_HTML_STRUCT,
    STEP_IMPROVER,
    STEP_META_GEN,
    STEP_PRIMARY_GEN,
    STEP_READER_OPINION,
    STEP_SCRAPING,
)
from app.services.pipeline.persistence import add_log
from app.services.template_engine import get_template_for_reference

MAX_COMPETITOR_TITLES = 10
MAX_COMPETITOR_DESCRIPTIONS = 10
MAX_PAA_WITH_ANSWERS = 8
MAX_HIGHLIGHTED_KEYWORDS = 30
MAX_AI_OVERVIEW_CHARS = 2000
MAX_ANSWER_BOX_CHARS = 500
MAX_KG_FACTS = 15


def _safe_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return [item for item in val if item is not None]
    return []


def apply_template_vars(text: str, variables: dict) -> tuple[str, dict]:
    if not text:
        return text, {"resolved": [], "unresolved": [], "empty": []}

    resolved = []
    unresolved = []
    empty = []

    def replacer(match):
        key = match.group(1).strip()
        if key in variables:
            val = variables[key]
            if val is None or val == "" or val == [] or val == {}:
                if key not in empty:
                    empty.append(key)
            else:
                str_val = str(val)
                resolved.append(f'{key}="{str_val[:100]}..."' if len(str_val) > 100 else f'{key}="{str_val}"')
            return str(val)
        if key not in unresolved:
            unresolved.append(key)
        return match.group(0)

    replaced_text = re.sub(r"\{\{(.+?)\}\}", replacer, text)
    report = {"resolved": list(set(resolved)), "unresolved": unresolved, "empty": empty}
    return replaced_text, report


def setup_vars(ctx):
    try:
        scrape_info = ctx.outline_data.get("scrape_info", {}) if isinstance(ctx.outline_data, dict) else {}
        avg_words = scrape_info.get("avg_words", 800)
        headers_info = scrape_info.get("headers", [])

        raw_serp = ctx.task.serp_data
        if not isinstance(raw_serp, dict):
            print(f"WARNING: serp_data is {type(raw_serp).__name__}, forcing empty dict. task_id={ctx.task_id}")
            serp = {}
        else:
            serp = raw_serp

        def _safe_list_inner(val):
            if isinstance(val, list):
                return [item for item in val if item is not None]
            if val is None:
                return []
            print(f"WARNING: _safe_list got {type(val).__name__}: {str(val)[:100]}")
            return []

        related = _safe_list_inner(serp.get("related_searches"))
        organic_results = [r for r in _safe_list_inner(serp.get("organic_results")) if isinstance(r, dict)]
        paa_full = [p for p in _safe_list_inner(serp.get("paa_full")) if isinstance(p, dict)]
        featured_snippet = (
            serp.get("featured_snippet") if isinstance(serp.get("featured_snippet"), dict) else None
        )
        knowledge_graph = (
            serp.get("knowledge_graph") if isinstance(serp.get("knowledge_graph"), dict) else None
        )
        ai_overview = serp.get("ai_overview") if isinstance(serp.get("ai_overview"), dict) else None
        answer_box = serp.get("answer_box") if isinstance(serp.get("answer_box"), dict) else None
        serp_features = _safe_list_inner(serp.get("serp_features"))
        intent_signals = (
            serp.get("search_intent_signals") if isinstance(serp.get("search_intent_signals"), dict) else {}
        )

        competitor_titles = []
        for r in organic_results:
            t = r.get("title")
            if isinstance(t, str) and t.strip():
                competitor_titles.append(t)
            if len(competitor_titles) >= MAX_COMPETITOR_TITLES:
                break

        competitor_descriptions = []
        for r in organic_results:
            d = r.get("description")
            if isinstance(d, str) and d.strip():
                competitor_descriptions.append(d)
            if len(competitor_descriptions) >= MAX_COMPETITOR_DESCRIPTIONS:
                break

        step_results = ctx.task.step_results or {}
        scraping_step = step_results.get(STEP_SCRAPING, {})
        scraping_result_raw = scraping_step.get("result") if isinstance(scraping_step, dict) else None
        scraping_result = {}
        if isinstance(scraping_result_raw, str) and scraping_result_raw.strip():
            try:
                parsed_scraping = json.loads(scraping_result_raw)
                if isinstance(parsed_scraping, dict):
                    scraping_result = parsed_scraping
            except Exception:
                scraping_result = {}
        elif isinstance(scraping_result_raw, dict):
            scraping_result = scraping_result_raw

        scraped_titles = [
            t.strip()
            for t in _safe_list_inner(scraping_result.get("scraped_titles"))
            if isinstance(t, str) and t.strip()
        ]
        scraped_descriptions = [
            d.strip()
            for d in _safe_list_inner(scraping_result.get("scraped_descriptions"))
            if isinstance(d, str) and d.strip()
        ]

        if not competitor_titles and scraped_titles:
            competitor_titles = scraped_titles[:MAX_COMPETITOR_TITLES]
            add_log(
                ctx.db,
                ctx.task,
                f"competitor_titles fallback: {len(competitor_titles)} from scraping (SERP had none)",
                level="warning",
                step=STEP_SCRAPING,
            )

        if not competitor_descriptions and scraped_descriptions:
            competitor_descriptions = scraped_descriptions[:MAX_COMPETITOR_DESCRIPTIONS]
            add_log(
                ctx.db,
                ctx.task,
                f"competitor_descriptions fallback: {len(competitor_descriptions)} from scraping (SERP had none)",
                level="warning",
                step=STEP_SCRAPING,
            )

        highlighted_keywords = []
        for r in organic_results:
            if not r or not isinstance(r, dict):
                continue
            hl = r.get("highlighted")
            if isinstance(hl, list):
                for kw in hl:
                    if isinstance(kw, str) and kw.strip() and kw not in highlighted_keywords:
                        highlighted_keywords.append(kw)
        highlighted_keywords = list(set(highlighted_keywords))[:MAX_HIGHLIGHTED_KEYWORDS]

        auto_additional = ""
        deduped = []
        if not ctx.task.additional_keywords:
            lsi_parts = []
            if highlighted_keywords:
                lsi_parts.extend(highlighted_keywords[:15])
            if related:
                lsi_parts.extend(related[:10])
            main_kw_lower = ctx.task.main_keyword.lower()
            seen = set()
            for kw in lsi_parts:
                if not isinstance(kw, str):
                    continue
                kw_lower = kw.lower().strip()
                if kw_lower and kw_lower != main_kw_lower and kw_lower not in seen:
                    seen.add(kw_lower)
                    deduped.append(kw.strip())
            auto_additional = ", ".join(deduped[:20])

        if auto_additional and not ctx.task.additional_keywords:
            add_log(
                ctx.db,
                ctx.task,
                f"Auto-generated additional_keywords from SERP data ({len(deduped)} keywords)",
                level="info",
                step="setup_vars",
            )

        paa_with_answers = (
            "\n".join(
                [
                    f"Q: {p['question']}\nA: {p['answer']}"
                    for p in paa_full
                    if isinstance(p, dict) and p.get("answer")
                ][:MAX_PAA_WITH_ANSWERS]
            )
            if paa_full
            else ""
        )

        add_kw_text = f"\nAdditional Keywords: {ctx.task.additional_keywords}" if ctx.task.additional_keywords else ""

        ctx.base_context = (
            f"Keyword: {ctx.task.main_keyword}{add_kw_text}\n"
            f"Country: {ctx.task.country}\n"
            f"Language: {ctx.task.language}\n"
            f"SERP Features Present: {json.dumps(serp_features)}\n"
            f"Search Intent Signals: {json.dumps(intent_signals)}\n"
            f"Competitor Titles: {json.dumps(competitor_titles, ensure_ascii=False)}\n"
            f"Competitor Descriptions: {json.dumps(competitor_descriptions, ensure_ascii=False)}\n"
            f"Google Highlighted Keywords: {json.dumps(highlighted_keywords, ensure_ascii=False)}\n"
            f"People Also Ask (with answers):\n{paa_with_answers}\n"
            f"Related Searches: {json.dumps(related, ensure_ascii=False)}\n"
            f"Competitors Headers: {json.dumps(headers_info, ensure_ascii=False)}\n"
            f"Target word count: {avg_words}"
        )

        if featured_snippet:
            ctx.base_context += (
                f"\n\nFeatured Snippet (Google's preferred answer):\n"
                f"Type: {featured_snippet.get('type')}\n"
                f"Title: {featured_snippet.get('title')}\n"
                f"Text: {featured_snippet.get('description')}\n"
                f"Source: {featured_snippet.get('domain')}"
            )

        if knowledge_graph:
            facts = knowledge_graph.get("facts", [])[:MAX_KG_FACTS]
            ctx.base_context += (
                f"\n\nKnowledge Graph:\n"
                f"Entity: {knowledge_graph.get('title')}"
                f" ({knowledge_graph.get('subtitle', '')})\n"
                f"Description: {knowledge_graph.get('description', '')}\n"
                f"Facts: {json.dumps(facts, ensure_ascii=False)}"
            )

        if ai_overview:
            ctx.base_context += (
                f"\n\nGoogle AI Overview:\n{ai_overview.get('text', '')[:MAX_AI_OVERVIEW_CHARS]}"
            )

        if answer_box:
            ctx.base_context += f"\n\nAnswer Box:\n{answer_box.get('text', '')[:MAX_ANSWER_BOX_CHARS]}"

        ctx.analysis_vars = {
            "keyword": ctx.task.main_keyword,
            "additional_keywords": ctx.task.additional_keywords or auto_additional or "",
            "country": ctx.task.country,
            "language": ctx.task.language,
            "exclude_words": settings.EXCLUDE_WORDS,
            "site_name": ctx.site_name,
            "page_type": ctx.task.page_type,
            "competitors_headers": json.dumps(headers_info, ensure_ascii=False),
            "merged_markdown": ctx.task.competitors_text or "",
            "avg_word_count": str(avg_words),
            "competitor_titles": json.dumps(competitor_titles, ensure_ascii=False),
            "competitor_descriptions": json.dumps(competitor_descriptions, ensure_ascii=False),
            "highlighted_keywords": json.dumps(highlighted_keywords, ensure_ascii=False),
            "paa_with_answers": paa_with_answers,
            "featured_snippet": json.dumps(featured_snippet, ensure_ascii=False) if featured_snippet else "",
            "knowledge_graph": json.dumps(knowledge_graph, ensure_ascii=False) if knowledge_graph else "",
            "ai_overview": ai_overview.get("text", "")[:MAX_AI_OVERVIEW_CHARS] if ai_overview else "",
            "answer_box": answer_box.get("text", "")[:MAX_ANSWER_BOX_CHARS] if answer_box else "",
            "serp_features": json.dumps(serp_features),
            "search_intent_signals": json.dumps(intent_signals),
            "related_searches": json.dumps(related, ensure_ascii=False),
            "people_also_search": json.dumps(_safe_list_inner(serp.get("people_also_search")), ensure_ascii=False),
        }

        if not ctx.analysis_vars.get("additional_keywords"):
            ctx.analysis_vars["additional_keywords"] = ctx.task.main_keyword

        if isinstance(ctx.outline_data, dict):
            if ctx.outline_data.get("ai_structure"):
                ctx.analysis_vars["result_ai_structure_analysis"] = str(ctx.outline_data["ai_structure"])[:300]
            if ctx.outline_data.get("chunk_analysis"):
                ctx.analysis_vars["result_chunk_cluster_analysis"] = str(ctx.outline_data["chunk_analysis"])[:300]
            if ctx.outline_data.get("competitor_structure"):
                ctx.analysis_vars["result_competitor_structure_analysis"] = str(
                    ctx.outline_data["competitor_structure"]
                )[:300]
            if ctx.outline_data.get("final_structure"):
                ctx.analysis_vars["result_final_structure_analysis"] = str(ctx.outline_data["final_structure"])[:300]
            parsed = ctx.outline_data.get("ai_structure_parsed", {})
            if isinstance(parsed, dict):
                for key in ("intent", "Taxonomy", "Attention", "structura"):
                    if parsed.get(key):
                        ctx.analysis_vars[key] = str(parsed[key])[:300]

    except Exception as e:
        print(f"CRITICAL: setup_vars failed: {e}. Using empty defaults. task_id={ctx.task_id}")
        import traceback

        print(traceback.format_exc())
        ctx.analysis_vars = {
            "keyword": ctx.task.main_keyword,
            "additional_keywords": ctx.task.additional_keywords or ctx.task.main_keyword,
            "country": ctx.task.country,
            "language": ctx.task.language,
            "exclude_words": settings.EXCLUDE_WORDS,
            "site_name": ctx.site_name,
            "page_type": ctx.task.page_type,
            "competitors_headers": "[]",
            "merged_markdown": ctx.task.competitors_text or "",
            "avg_word_count": "800",
            "competitor_titles": "[]",
            "competitor_descriptions": "[]",
            "highlighted_keywords": "[]",
            "paa_with_answers": "",
            "featured_snippet": "",
            "knowledge_graph": "",
            "ai_overview": "",
            "answer_box": "",
            "serp_features": "[]",
            "search_intent_signals": "{}",
            "related_searches": "[]",
        }
        if isinstance(ctx.outline_data, dict):
            if ctx.outline_data.get("ai_structure"):
                ctx.analysis_vars["result_ai_structure_analysis"] = str(ctx.outline_data["ai_structure"])[:300]
            if ctx.outline_data.get("chunk_analysis"):
                ctx.analysis_vars["result_chunk_cluster_analysis"] = str(ctx.outline_data["chunk_analysis"])[:300]
            if ctx.outline_data.get("competitor_structure"):
                ctx.analysis_vars["result_competitor_structure_analysis"] = str(
                    ctx.outline_data["competitor_structure"]
                )[:300]
            if ctx.outline_data.get("final_structure"):
                ctx.analysis_vars["result_final_structure_analysis"] = str(ctx.outline_data["final_structure"])[:300]


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
