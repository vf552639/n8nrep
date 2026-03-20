import json
import traceback
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

from app.models.task import Task
from app.models.article import GeneratedArticle
from app.models.site import Site
from app.models.author import Author
from app.models.prompt import Prompt
from app.models.blueprint import BlueprintPage
from app.models.project import SiteProject

from app.services.serp import fetch_serp_data
from app.services.scraper import scrape_urls
from app.services.llm import generate_text
from app.services.template_engine import generate_full_page, get_template_for_reference
from app.services.notifier import notify_task_success, notify_task_failed
from app.services.deduplication import ContentDeduplicator
from app.config import settings

from app.services.json_parser import clean_and_parse_json
from app.services.pipeline_constants import *
import re
import datetime

class PipelineContext:
    def __init__(self, db: Session, task_id: str):
        self.db = db
        self.task_id = task_id
        
        self.task = db.query(Task).filter(Task.id == task_id).first()
        if not self.task:
            raise ValueError(f"Task {task_id} not found")
            
        self.site = db.query(Site).filter(Site.id == self.task.target_site_id).first()
        self.site_name = self.site.name if self.site else "Unknown Site"
        
        self.blueprint_page = None
        self.all_site_pages = []
        self.page_slug = ""
        self.page_title = ""
        self.use_serp = True
        
        if self.task.blueprint_page_id and self.task.project_id:
            self.blueprint_page = db.query(BlueprintPage).filter(BlueprintPage.id == self.task.blueprint_page_id).first()
            if self.blueprint_page:
                self.page_slug = self.blueprint_page.page_slug
                self.page_title = self.blueprint_page.page_title
                self.use_serp = self.blueprint_page.use_serp
                
                project = db.query(SiteProject).filter(SiteProject.id == self.task.project_id).first()
                if project:
                    all_pages_db = db.query(BlueprintPage).filter(BlueprintPage.blueprint_id == project.blueprint_id).order_by(BlueprintPage.sort_order).all()
                    self.all_site_pages = [{"slug": p.page_slug, "title": p.page_title, "type": p.page_type, "url": p.filename} for p in all_pages_db]
                    
        self.analysis_vars = {}
        self.template_vars = {}
        self.outline_data = self.task.outline or {}

def get_prompt_obj(db: Session, agent_name: str) -> Prompt:
    prompt_obj = db.query(Prompt).filter(Prompt.agent_name == agent_name, Prompt.is_active == True).first()
    if not prompt_obj:
        raise Exception(f"No active prompt found for agent: {agent_name}")
    return prompt_obj

def save_step_result(db: Session, task: Task, step_name: str, result: str, model: str = None, status: str = "completed", cost: float = 0.0, variables_snapshot: dict = None, resolved_prompts: dict = None, exclude_words_violations: dict = None):
    if task.step_results is None:
        task.step_results = {}
    
    step_data = {
        "status": status,
        "result": result[:50000] if result else None,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    if model:
        step_data["model"] = model
    if cost > 0:
        step_data["cost"] = cost
    if variables_snapshot:
        step_data["variables_snapshot"] = variables_snapshot
    if resolved_prompts:
        step_data["resolved_prompts"] = resolved_prompts
    if exclude_words_violations:
        step_data["exclude_words_violations"] = exclude_words_violations
    
    updated = dict(task.step_results)
    updated[step_name] = step_data
    task.step_results = updated
    db.commit() # Required to trigger SQLAlchemy JSON updates safely without flag_modified

def add_log(db: Session, task: Task, msg: str, level: str = "info", step: str = None):
    entry = {
        "ts": datetime.datetime.utcnow().isoformat(),
        "level": level,
        "msg": msg,
    }
    if step:
        entry["step"] = step
    
    current_logs = list(task.logs or [])
    current_logs.append(entry)
    task.logs = current_logs
    db.commit()

from typing import Tuple

def apply_template_vars(text: str, variables: dict) -> Tuple[str, dict]:
    """Replace {{variable_name}} placeholders in text with actual values and return a resolution report."""
    if not text:
        return text, {"resolved": [], "unresolved": [], "empty": []}
        
    resolved = []
    unresolved = []
    empty = []
    
    def replacer(match):
        key = match.group(1).strip()
        if key in variables:
            val = variables[key]
            # Check if empty (None, "", [], {})
            if val is None or val == "" or val == [] or val == {}:
                if key not in empty:
                    empty.append(key)
            else:
                str_val = str(val)
                resolved.append(f'{key}="{str_val[:100]}..."' if len(str_val) > 100 else f'{key}="{str_val}"')
            return str(val)
        else:
            if key not in unresolved:
                unresolved.append(key)
            return match.group(0)  # keep original if not found
            
    replaced_text = re.sub(r'\{\{(.+?)\}\}', replacer, text)
    report = {
        "resolved": list(set(resolved)),
        "unresolved": unresolved,
        "empty": empty
    }
    return replaced_text, report

def call_agent(ctx: PipelineContext, agent_name: str, context: str, response_format=None, variables: dict = None) -> Tuple[str, float, str, dict, dict]:
    """Helper: load prompt config for agent_name, apply template vars, merge context, call LLM."""
    prompt = get_prompt_obj(ctx.db, agent_name)
    
    if getattr(prompt, "skip_in_pipeline", False):
        print(f"Agent {agent_name} skipped (toggle off)")
        return "", 0.0, prompt.model, {}, {}
    
    system_text = prompt.system_prompt
    user_template = prompt.user_prompt or ""
    
    resolved_prompts = {}
    variables_snapshot = {}
    
    if variables:
        system_text, sys_report = apply_template_vars(system_text, variables)
        user_template, user_report = apply_template_vars(user_template, variables)
        
        # Merge reports
        all_resolved = list(set(sys_report["resolved"] + user_report["resolved"]))
        all_unresolved = list(set(sys_report["unresolved"] + user_report["unresolved"]))
        all_empty = list(set(sys_report["empty"] + user_report["empty"]))
        
        log_msg = f"[VARS] agent={agent_name}"
        log_msg += f" | resolved: {', '.join(all_resolved) if all_resolved else '(none)'}"
        log_msg += f" | empty: {', '.join(all_empty) if all_empty else '(none)'}"
        log_msg += f" | unresolved: {', '.join(all_unresolved) if all_unresolved else '(none)'}"
        
        level = "info"
        if all_unresolved:
            level = "warn"
            
        add_log(ctx.db, ctx.task, log_msg, level=level, step=agent_name)
        
        # Check Critical Vars
        critical = CRITICAL_VARS.get(agent_name, [])
        missing_critical = []
        for cv in critical:
            if cv in all_unresolved or cv in all_empty:
                missing_critical.append(cv)
                
        if missing_critical:
            err_msg = f"CRITICAL VARIABLES MISSING OR EMPTY for {agent_name}: {', '.join(missing_critical)}"
            add_log(ctx.db, ctx.task, err_msg, level="error", step=agent_name)
            if getattr(settings, "STRICT_VARIABLE_CHECK", False):
                raise ValueError(err_msg)
                
        # Create truncated snapshot
        for k, v in variables.items():
            val_str = str(v)
            variables_snapshot[k] = val_str[:200] + "..." if len(val_str) > 200 else val_str
            
        # --- INJECT EXCLUDE WORDS INTO PROMPT ---
        exclude_str = variables.get("exclude_words", "")
        if exclude_str.strip():
            words_list = [w.strip() for w in exclude_str.split(",") if w.strip()]
            if words_list:
                exclude_instruction = (
                    "\n\n[BANNED WORDS — CRITICAL RULE]\n"
                    "You MUST NOT use ANY of the following words in your output, "
                    "in any form (including variations, plurals, different cases). "
                    "These words are strictly forbidden and their presence will cause "
                    "the output to be rejected:\n"
                    f"{', '.join(words_list)}\n"
                    "Use synonyms or rephrase completely. "
                    "This rule has the HIGHEST priority and overrides all other instructions."
                )
                system_text += exclude_instruction
        # --- END INJECT ---
        
        if agent_name == "final_editing":
            schema_instruction = (
                "\n\n[SCHEMA/JSON-LD PROHIBITION — CRITICAL RULE]\n"
                "You MUST NOT include any Schema.org markup, JSON-LD scripts, "
                "or placeholder blocks like [SCHEMA: ...], [🛠️ SCHEMA: ...], "
                "<script type=\"application/ld+json\">, or any references to structured data markup "
                "in your output. Do NOT suggest, mention, or output any Schema.org related content. "
                "Your output must be pure article HTML only (p, h2, h3, ul, ol, strong, em, a tags). "
                "This rule has the HIGHEST priority."
            )
            system_text += schema_instruction
    
    user_msg = f"{user_template}\n\n[CONTEXT]\n{context}" if user_template else context
    
    # --- INJECT RERUN FEEDBACK ---
    step_results = ctx.task.step_results or {}
    rerun_feedback = step_results.get("_rerun_feedback", {})
    if rerun_feedback.get("step") == agent_name and rerun_feedback.get("feedback"):
        user_msg += f"\n\n[HUMAN FEEDBACK ON PREVIOUS VERSION]\n{rerun_feedback['feedback']}"
        add_log(ctx.db, ctx.task, f"Injected human feedback into prompt for {agent_name}", level="info", step=agent_name)
        
        # Clear it so we don't apply it again later
        new_results = dict(step_results)
        del new_results["_rerun_feedback"]
        ctx.task.step_results = new_results
        ctx.db.commit()
    # -----------------------------
    
    resolved_prompts["system_prompt"] = system_text[:6000]
    resolved_prompts["user_prompt"] = user_msg[:6000]
    
    # Log context size for diagnostics
    total_chars = len(system_text) + len(user_msg)
    print(f"[call_agent] {agent_name} | model={prompt.model} | "
          f"system={len(system_text)} chars | user={len(user_msg)} chars | "
          f"total={total_chars} chars (~{total_chars // 4} tokens est.)")
    
    kwargs = {
        "system_prompt": system_text,
        "user_prompt": user_msg,
        "model": prompt.model,
        "temperature": prompt.temperature,
        "frequency_penalty": prompt.frequency_penalty,
        "presence_penalty": prompt.presence_penalty,
        "top_p": prompt.top_p,
    }
    if response_format:
        kwargs["response_format"] = response_format
    
    res, cost, model = generate_text(**kwargs)
    return res, cost, model, resolved_prompts, variables_snapshot

def call_agent_with_exclude_validation(ctx: PipelineContext, agent_name: str, context: str, step_constant: str, max_retries: int = 1):
    from app.services.exclude_words_validator import ExcludeWordsValidator
    
    result_text, total_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, agent_name, context, variables=ctx.template_vars)
    
    exclude_str = ctx.template_vars.get("exclude_words", "")
    if not exclude_str.strip():
        return result_text, total_cost, actual_model, resolved_prompts, variables_snapshot, None
        
    validator = ExcludeWordsValidator(exclude_str)
    report = validator.validate(result_text)
    
    if report["passed"]:
        return result_text, total_cost, actual_model, resolved_prompts, variables_snapshot, None
        
    add_log(ctx.db, ctx.task, f"EXCLUDE_WORDS violation: found {report['found_words']}", level="warn", step=step_constant)
    
    retry_count = 0
    while retry_count < max_retries and not report["passed"]:
        retry_count += 1
        add_log(ctx.db, ctx.task, f"Retrying agent {agent_name} due to exclude words violation (Attempt {retry_count}).", level="info", step=step_constant)
        
        retry_context = context + f"\n\nCRITICAL: Your previous output contained forbidden words: {report['found_words']}. You MUST NOT use these words. Rewrite the text avoiding them completely."
        
        retry_text, retry_cost, r_model, r_prompts, r_vars = call_agent(ctx, agent_name, retry_context, variables=ctx.template_vars)
        total_cost += retry_cost
        result_text = retry_text
        actual_model = r_model
        resolved_prompts = r_prompts
        variables_snapshot = r_vars
        
        report = validator.validate(result_text)
        
    violations_dict = None
    if not report["passed"]:
        add_log(ctx.db, ctx.task, f"EXCLUDE_WORDS violation persists after retries: found {report['found_words']}", level="error", step=step_constant)
        violations_dict = report["found_words"]
        
    return result_text, total_cost, actual_model, resolved_prompts, variables_snapshot, violations_dict

MAX_COMPETITOR_TITLES = 10
MAX_COMPETITOR_DESCRIPTIONS = 10
MAX_PAA_WITH_ANSWERS = 8
MAX_HIGHLIGHTED_KEYWORDS = 30
MAX_AI_OVERVIEW_CHARS = 2000
MAX_ANSWER_BOX_CHARS = 500
MAX_KG_FACTS = 15

def _safe_list(val) -> list:
    """Guarantees a list return even if val is None, a string, a number, etc."""
    if val is None:
        return []
    if isinstance(val, list):
        return [item for item in val if item is not None]
    return []

def setup_vars(ctx: PipelineContext):
    try:
        scrape_info = ctx.outline_data.get("scrape_info", {}) if isinstance(ctx.outline_data, dict) else {}
        avg_words = scrape_info.get("avg_words", 800)
        headers_info = scrape_info.get("headers", [])
        
        # === CRITICAL: Force safe dict ===
        raw_serp = ctx.task.serp_data
        if not isinstance(raw_serp, dict):
            print(f"WARNING: serp_data is {type(raw_serp).__name__}, forcing empty dict. task_id={ctx.task_id}")
            serp = {}
        else:
            serp = raw_serp

        def _safe_list(val):
            """Guarantee a list return, even if val is any unexpected type."""
            if isinstance(val, list):
                return [item for item in val if item is not None]
            if val is None:
                return []
            # val is a string, int, dict, or something else unexpected
            print(f"WARNING: _safe_list got {type(val).__name__}: {str(val)[:100]}")
            return []

        paa = _safe_list(serp.get("paa"))
        related = _safe_list(serp.get("related_searches"))
        organic_results = [r for r in _safe_list(serp.get("organic_results")) if isinstance(r, dict)]
        paa_full = [p for p in _safe_list(serp.get("paa_full")) if isinstance(p, dict)]
        featured_snippet = serp.get("featured_snippet") if isinstance(serp.get("featured_snippet"), dict) else None
        knowledge_graph = serp.get("knowledge_graph") if isinstance(serp.get("knowledge_graph"), dict) else None
        ai_overview = serp.get("ai_overview") if isinstance(serp.get("ai_overview"), dict) else None
        answer_box = serp.get("answer_box") if isinstance(serp.get("answer_box"), dict) else None
        serp_features = _safe_list(serp.get("serp_features"))
        intent_signals = serp.get("search_intent_signals") if isinstance(serp.get("search_intent_signals"), dict) else {}

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
        
        paa_with_answers = "\n".join([
            f"Q: {p['question']}\nA: {p['answer']}" 
            for p in paa_full if isinstance(p, dict) and p.get("answer")
        ][:MAX_PAA_WITH_ANSWERS]) if paa_full else ""
        
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
            facts = knowledge_graph.get('facts', [])[:MAX_KG_FACTS]
            ctx.base_context += (
                f"\n\nKnowledge Graph:\n"
                f"Entity: {knowledge_graph.get('title')}"
                f" ({knowledge_graph.get('subtitle', '')})\n"
                f"Description: {knowledge_graph.get('description', '')}\n"
                f"Facts: {json.dumps(facts, ensure_ascii=False)}"
            )
            
        if ai_overview:
            ctx.base_context += (
                f"\n\nGoogle AI Overview:\n"
                f"{ai_overview.get('text', '')[:MAX_AI_OVERVIEW_CHARS]}"
            )
            
        if answer_box:
            ctx.base_context += (
                f"\n\nAnswer Box:\n"
                f"{answer_box.get('text', '')[:MAX_ANSWER_BOX_CHARS]}"
            )

        ctx.analysis_vars = {
            "keyword": ctx.task.main_keyword,
            "additional_keywords": ctx.task.additional_keywords or "",
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
        }

        # Restore results from previous pipeline phases (setup_vars recreates analysis_vars from scratch)
        if isinstance(ctx.outline_data, dict):
            if ctx.outline_data.get("ai_structure"):
                ctx.analysis_vars["result_ai_structure_analysis"] = str(ctx.outline_data["ai_structure"])[:300]
            if ctx.outline_data.get("chunk_analysis"):
                ctx.analysis_vars["result_chunk_cluster_analysis"] = str(ctx.outline_data["chunk_analysis"])[:300]
            if ctx.outline_data.get("competitor_structure"):
                ctx.analysis_vars["result_competitor_structure_analysis"] = str(ctx.outline_data["competitor_structure"])[:300]
            if ctx.outline_data.get("final_structure"):
                ctx.analysis_vars["result_final_structure_analysis"] = str(ctx.outline_data["final_structure"])[:300]
            # Parsed sub-variables from ai_structure
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
            "additional_keywords": ctx.task.additional_keywords or "",
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
        # Restore results even in fallback
        if isinstance(ctx.outline_data, dict):
            if ctx.outline_data.get("ai_structure"):
                ctx.analysis_vars["result_ai_structure_analysis"] = str(ctx.outline_data["ai_structure"])[:300]
            if ctx.outline_data.get("chunk_analysis"):
                ctx.analysis_vars["result_chunk_cluster_analysis"] = str(ctx.outline_data["chunk_analysis"])[:300]
            if ctx.outline_data.get("competitor_structure"):
                ctx.analysis_vars["result_competitor_structure_analysis"] = str(ctx.outline_data["competitor_structure"])[:300]
            if ctx.outline_data.get("final_structure"):
                ctx.analysis_vars["result_final_structure_analysis"] = str(ctx.outline_data["final_structure"])[:300]

def setup_template_vars(ctx: PipelineContext):
    # Defaults in case no author is assigned
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
        "additional_keywords": ctx.task.additional_keywords or "",
        "country": ctx.task.country,
        "language": ctx.task.language,
        "page_type": ctx.task.page_type,
        "competitors_headers": json.dumps(ctx.task.outline.get('scrape_info', {}).get('headers', []), ensure_ascii=False),
        "merged_markdown": ctx.task.competitors_text or "",
        "avg_word_count": str(ctx.task.outline.get('scrape_info', {}).get('avg_words', 800)),
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
        "result_final_structure_analysis": ctx.task.outline.get("final_structure", json.dumps(ctx.task.outline.get("final_outline", {}), ensure_ascii=False)),
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
        "structure_fact_checking": ""
    }

    # Fetch HTML template reference for LLM injection
    site_template_html, site_template_name = get_template_for_reference(ctx.db, str(ctx.task.target_site_id))
    ctx.template_vars["site_template_html"] = site_template_html or ""
    ctx.template_vars["site_template_name"] = site_template_name or ""

def run_phase(db: Session, task: Task, step_key: str, phase_func, *args, **kwargs):
    """Wrapper that skips phase_func if already completed."""
    if task.step_results and step_key in task.step_results:
        if task.step_results[step_key].get("status") == "completed":
            print(f"Skipping {step_key} - already completed")
            return
            
    print(f"Running phase: {step_key}")
    task.last_heartbeat = datetime.datetime.utcnow()
    db.commit()
    phase_func(*args, **kwargs)

def phase_serp(ctx: PipelineContext):
    if not ctx.task.serp_data:
        add_log(ctx.db, ctx.task, "Fetching SERP data...", step=STEP_SERP)
        save_step_result(ctx.db, ctx.task, STEP_SERP, result=None, status="running")
        serp_data = fetch_serp_data(ctx.task.main_keyword, ctx.task.country, ctx.task.language)
        ctx.task.serp_data = serp_data
        ctx.db.commit()
        add_log(ctx.db, ctx.task, f"SERP Research completed.", step=STEP_SERP)
        # Save summary for step_result (full data in task.serp_data)
        def _safe_len(val) -> int:
            return len(val) if isinstance(val, list) else 0

        serp_summary = {
            "source": serp_data.get("source", "unknown") if isinstance(serp_data, dict) else "unknown",
            "urls_count": _safe_len(serp_data.get("urls")) if isinstance(serp_data, dict) else 0,
            "organic_count": _safe_len(serp_data.get("organic_results")) if isinstance(serp_data, dict) else 0,
            "paa_count": _safe_len(serp_data.get("paa_full")) if isinstance(serp_data, dict) else 0,
            "related_count": _safe_len(serp_data.get("related_searches")) if isinstance(serp_data, dict) else 0,
            "has_featured_snippet": serp_data.get("featured_snippet") is not None if isinstance(serp_data, dict) else False,
            "has_knowledge_graph": serp_data.get("knowledge_graph") is not None if isinstance(serp_data, dict) else False,
            "has_ai_overview": serp_data.get("ai_overview") is not None if isinstance(serp_data, dict) else False,
            "has_answer_box": serp_data.get("answer_box") is not None if isinstance(serp_data, dict) else False,
            "serp_features": _safe_list(serp_data.get("serp_features")) if isinstance(serp_data, dict) else [],
            "urls": _safe_list(serp_data.get("urls")) if isinstance(serp_data, dict) else [],
        }
        save_step_result(ctx.db, ctx.task, STEP_SERP, result=json.dumps(serp_summary, ensure_ascii=False), status="completed")

def phase_scraping(ctx: PipelineContext):
    if not ctx.task.competitors_text:
        urls = ctx.task.serp_data.get("urls", [])
        if not urls:
            raise Exception("No URLs found in SERP data")
        
        add_log(ctx.db, ctx.task, f"Scraping {len(urls)} competitors...", step=STEP_SCRAPING)
        save_step_result(ctx.db, ctx.task, STEP_SCRAPING, result=None, status="running")
    
        scrape_data = scrape_urls(urls)
        ctx.task.competitors_text = scrape_data["merged_text"]
    
        ctx.task.outline = {
            "scrape_info": {
                "avg_words": scrape_data["average_word_count"],
                "headers": scrape_data["headers_structure"]
            }
        }
        ctx.db.commit()
        ctx.outline_data = ctx.task.outline
        
        scrape_summary = {
            "total_from_serp": len(urls),
            "total_attempted": scrape_data["total_attempted"],
            "successful": scrape_data["successful_scrapes"],
            "failed": scrape_data["total_attempted"] - scrape_data["successful_scrapes"],
            "avg_word_count": scrape_data["average_word_count"],
            "scraped_domains": [r["domain"] for r in scrape_data["raw_results"]],
            "scraped_urls": [r["url"] for r in scrape_data["raw_results"]],
            "failed_results": scrape_data.get("failed_results", []),
            "serper_count": scrape_data.get("serper_count", 0),
            "direct_count": scrape_data.get("direct_count", 0),
        }

        add_log(ctx.db, ctx.task, f"Scraped competitors. Avg word count: {scrape_data['average_word_count']}", step=STEP_SCRAPING)
        save_step_result(ctx.db, ctx.task, STEP_SCRAPING, result=json.dumps(scrape_summary, ensure_ascii=False), status="completed")

def phase_ai_structure(ctx: PipelineContext):
    ctx.db.refresh(ctx.task)  # Force reload from DB
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting AI Structure Analysis...", step=STEP_AI_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_AI_ANALYSIS, result=None, status="running")
    ai_structure, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, "ai_structure_analysis", ctx.base_context, 
        response_format={"type": "json_object"}, variables=ctx.analysis_vars
    )
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    ctx.analysis_vars["result_ai_structure_analysis"] = ai_structure
    ctx.outline_data["ai_structure"] = ai_structure
    
    add_log(ctx.db, ctx.task, f"ai_structure raw (first 500): {ai_structure[:500]}", level="debug", step=STEP_AI_ANALYSIS)
    
    ai_struct_data = clean_and_parse_json(ai_structure)
    if ai_struct_data:
        ctx.analysis_vars["intent"] = ai_struct_data.get("intent", "")
        ctx.analysis_vars["Taxonomy"] = ai_struct_data.get("Taxonomy", "")
        ctx.analysis_vars["Attention"] = ai_struct_data.get("Attention", "")
        ctx.analysis_vars["structura"] = ai_struct_data.get("structura", "")
        ctx.outline_data["ai_structure_parsed"] = ai_struct_data
        
        if not ai_struct_data.get("intent"):
            add_log(ctx.db, ctx.task, f"Warning: 'intent' is empty after parsing ai_structure", level="warn", step=STEP_AI_ANALYSIS)
    else:
        add_log(ctx.db, ctx.task, f"Warning: Failed to parse ai_structure_analysis JSON", level="warn", step=STEP_AI_ANALYSIS)

    ctx.task.outline = ctx.outline_data
    ctx.db.commit()
    
    final_status = "completed_with_warnings" if not ai_struct_data or not ai_struct_data.get("intent") else "completed"
    add_log(ctx.db, ctx.task, f"AI Structure Analysis completed ({len(ai_structure)} chars)", step=STEP_AI_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_AI_ANALYSIS, result=ai_structure, model=actual_model, status=final_status, cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_chunk_analysis(ctx: PipelineContext):
    ctx.db.refresh(ctx.task)  # Force reload from DB
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting Chunk Cluster Analysis...", step=STEP_CHUNK_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_CHUNK_ANALYSIS, result=None, status="running")
    ai_structure = ctx.outline_data.get("ai_structure", "")
    chunk_context = f"{ctx.base_context}\n\nAI Structure Analysis:\n{ai_structure}"
    chunk_analysis, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "chunk_cluster_analysis", chunk_context, variables=ctx.analysis_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    ctx.analysis_vars["result_chunk_cluster_analysis"] = chunk_analysis
    ctx.outline_data["chunk_analysis"] = chunk_analysis
    ctx.task.outline = ctx.outline_data
    ctx.db.commit()
    add_log(ctx.db, ctx.task, f"Chunk Cluster Analysis completed ({len(chunk_analysis)} chars)", step=STEP_CHUNK_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_CHUNK_ANALYSIS, result=chunk_analysis, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_competitor_structure(ctx: PipelineContext):
    ctx.db.refresh(ctx.task)  # Force reload from DB
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting Competitor Structure Analysis...", step=STEP_COMP_STRUCTURE)
    save_step_result(ctx.db, ctx.task, STEP_COMP_STRUCTURE, result=None, status="running")
    chunk_analysis = ctx.outline_data.get("chunk_analysis", "")
    competitor_context = (
        f"{ctx.base_context}\n\n"
        f"Competitors Text:\n{ctx.task.competitors_text[:20000]}\n\n"
        f"Chunk Analysis:\n{chunk_analysis}"
    )
    competitor_structure, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "competitor_structure_analysis", competitor_context, variables=ctx.analysis_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    ctx.analysis_vars["result_competitor_structure_analysis"] = competitor_structure
    ctx.outline_data["competitor_structure"] = competitor_structure
    ctx.task.outline = ctx.outline_data
    ctx.db.commit()
    add_log(ctx.db, ctx.task, f"Competitor Structure Analysis completed ({len(competitor_structure)} chars)", step=STEP_COMP_STRUCTURE)
    save_step_result(ctx.db, ctx.task, STEP_COMP_STRUCTURE, result=competitor_structure, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_final_structure(ctx: PipelineContext):
    ctx.db.refresh(ctx.task)  # Force reload from DB
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting Final Structure Analysis (JSON)...", step=STEP_FINAL_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_ANALYSIS, result=None, status="running")
    
    final_analysis_context = (
        f"{ctx.base_context}\n\n"
        f"AI Structure Analysis:\n{ctx.outline_data.get('ai_structure', '')}\n\n"
        f"Chunk Analysis:\n{ctx.outline_data.get('chunk_analysis', '')}\n\n"
        f"Competitor Structure Analysis:\n{ctx.outline_data.get('competitor_structure', '')}"
    )
    outline_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, "final_structure_analysis", final_analysis_context,
        response_format={"type": "json_object"}, variables=ctx.analysis_vars
    )
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    ctx.outline_data["final_outline"] = clean_and_parse_json(outline_json_str)
    ctx.outline_data["final_structure"] = outline_json_str
    ctx.task.outline = ctx.outline_data
    ctx.db.commit()
    add_log(ctx.db, ctx.task, f"Final Structure Analysis completed", step=STEP_FINAL_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_ANALYSIS, result=outline_json_str, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_structure_fact_check(ctx: PipelineContext):
    setup_template_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting Structure Fact-Checking...", step=STEP_STRUCTURE_FACT_CHECK)
    save_step_result(ctx.db, ctx.task, STEP_STRUCTURE_FACT_CHECK, result=None, status="running")
    
    fact_check_report, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "structure_fact_checking", "", variables=ctx.template_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Structure Fact-Checking completed ({len(fact_check_report)} chars)", step=STEP_STRUCTURE_FACT_CHECK)
    save_step_result(ctx.db, ctx.task, STEP_STRUCTURE_FACT_CHECK, result=fact_check_report, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_primary_gen(ctx: PipelineContext):
    setup_template_vars(ctx)
    outline_json = ctx.task.outline.get("final_outline", {})
    gen_context = (
        f"Keyword: {ctx.task.main_keyword}\n"
        f"Language: {ctx.task.language}\n"
        f"{ctx.author_block}\n"
        f"Outline: {json.dumps(outline_json, ensure_ascii=False)}"
    )
    add_log(ctx.db, ctx.task, "Starting Primary Generation...", step=STEP_PRIMARY_GEN)
    save_step_result(ctx.db, ctx.task, STEP_PRIMARY_GEN, result=None, status="running")
    draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = call_agent_with_exclude_validation(ctx, "primary_generation", gen_context, step_constant=STEP_PRIMARY_GEN)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Primary Generation completed ({len(draft_html)} chars)", step=STEP_PRIMARY_GEN)
    save_step_result(ctx.db, ctx.task, STEP_PRIMARY_GEN, result=draft_html, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts, exclude_words_violations=violations)

def phase_competitor_comparison(ctx: PipelineContext):
    setup_template_vars(ctx)
    draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
    comparison_context = (
        f"Our article:\n{draft_html}\n\n"
        f"Competitors:\n{ctx.task.competitors_text[:15000]}"
    )
    add_log(ctx.db, ctx.task, "Starting Competitor Comparison...", step=STEP_COMP_COMPARISON)
    save_step_result(ctx.db, ctx.task, STEP_COMP_COMPARISON, result=None, status="running")
    comparison_review, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "competitor_comparison", comparison_context, variables=ctx.template_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Competitor Comparison completed", step=STEP_COMP_COMPARISON)
    save_step_result(ctx.db, ctx.task, STEP_COMP_COMPARISON, result=comparison_review, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_reader_opinion(ctx: PipelineContext):
    setup_template_vars(ctx)
    draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
    reader_context = f"Article:\n{draft_html}"
    add_log(ctx.db, ctx.task, "Starting Reader Opinion analysis...", step=STEP_READER_OPINION)
    save_step_result(ctx.db, ctx.task, STEP_READER_OPINION, result=None, status="running")
    reader_feedback, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "reader_opinion", reader_context, variables=ctx.template_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Reader Opinion completed", step=STEP_READER_OPINION)
    save_step_result(ctx.db, ctx.task, STEP_READER_OPINION, result=reader_feedback, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_interlink(ctx: PipelineContext):
    setup_template_vars(ctx)
    draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
    interlink_context = (
        f"Article:\n{draft_html}\n\n"
        f"Keyword: {ctx.task.main_keyword}\n"
        f"Language: {ctx.task.language}\n"
        f"Site: {ctx.site_name}"
    )
    add_log(ctx.db, ctx.task, "Starting Interlinking & Citations...", step=STEP_INTERLINK)
    save_step_result(ctx.db, ctx.task, STEP_INTERLINK, result=None, status="running")
    interlink_suggestions, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "interlinking_citations", interlink_context, variables=ctx.template_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Interlinking & Citations completed", step=STEP_INTERLINK)
    save_step_result(ctx.db, ctx.task, STEP_INTERLINK, result=interlink_suggestions, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_improver(ctx: PipelineContext):
    setup_template_vars(ctx)
    draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
    comparison_review = ctx.task.step_results.get(STEP_COMP_COMPARISON, {}).get("result", "")
    reader_feedback = ctx.task.step_results.get(STEP_READER_OPINION, {}).get("result", "")
    interlink_suggestions = ctx.task.step_results.get(STEP_INTERLINK, {}).get("result", "")
    
    improver_context = (
        f"Draft:\n{draft_html}\n\n"
        f"Competitor Comparison Review:\n{comparison_review}\n\n"
        f"Reader Feedback:\n{reader_feedback}\n\n"
        f"Interlinking & Citations Suggestions:\n{interlink_suggestions}"
    )
    add_log(ctx.db, ctx.task, "Starting Improver (draft enhancement)...", step=STEP_IMPROVER)
    save_step_result(ctx.db, ctx.task, STEP_IMPROVER, result=None, status="running")
    improved_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = call_agent_with_exclude_validation(ctx, "improver", improver_context, step_constant=STEP_IMPROVER)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Improver completed ({len(improved_html)} chars)", step=STEP_IMPROVER)
    save_step_result(ctx.db, ctx.task, STEP_IMPROVER, result=improved_html, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts, exclude_words_violations=violations)

def phase_final_editing(ctx: PipelineContext):
    setup_template_vars(ctx)
    if ctx.use_serp:
        improved_html = ctx.task.step_results.get(STEP_IMPROVER, {}).get("result", "")
    else:
        improved_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
        
    outline_json = ctx.task.outline.get("final_outline", {})
    
    avg_words = ctx.template_vars.get("avg_word_count", "0")
    input_word_count = len(BeautifulSoup(improved_html, 'html.parser').get_text().split())
    input_char_count = len(improved_html)

    editing_context = (
        f"Improved HTML:\n{improved_html}\n\n"
        f"Original Outline:\n{json.dumps(outline_json, ensure_ascii=False)}\n\n"
        f"Target word count (competitor average): {avg_words} words\n"
        f"Current article stats: {input_word_count} words, {input_char_count} characters\n\n"
        f"Review & verify this HTML article matches the outline structure."
    )
    add_log(ctx.db, ctx.task, "Starting Final Editing...", step=STEP_FINAL_EDIT)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_EDIT, result=None, status="running")
    final_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = call_agent_with_exclude_validation(ctx, "final_editing", editing_context, step_constant=STEP_FINAL_EDIT)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    # Remove SCHEMA placeholder blocks and scripts
    final_html = re.sub(r'\[.*?SCHEMA.*?\]', '', final_html, flags=re.IGNORECASE | re.DOTALL)
    final_html = re.sub(r'<script[^>]*application/ld\+json[^>]*>.*?</script>', '', final_html, flags=re.IGNORECASE | re.DOTALL)
    final_html = re.sub(r'\n{3,}', '\n\n', final_html)

    # Force-remove any remaining exclude words as last resort
    exclude_str = ctx.template_vars.get("exclude_words", "")
    if exclude_str.strip():
        from app.services.exclude_words_validator import ExcludeWordsValidator
        validator = ExcludeWordsValidator(exclude_str)
        final_report = validator.validate(final_html)
        if not final_report["passed"]:
            add_log(ctx.db, ctx.task, 
                f"Force-removing remaining exclude words after final editing: {final_report['found_words']}", 
                level="warn", step=STEP_FINAL_EDIT)
            final_html, removal_report = validator.remove_violations(final_html)

    # Calculate output stats
    output_word_count = len(BeautifulSoup(final_html, 'html.parser').get_text().split())
    output_char_count = len(final_html)

    add_log(ctx.db, ctx.task, 
        f"Final Editing completed | input: {input_word_count} words / {input_char_count} chars | "
        f"output: {output_word_count} words / {output_char_count} chars | "
        f"target avg: {avg_words} words", 
        step=STEP_FINAL_EDIT)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_EDIT, result=final_html, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts, exclude_words_violations=violations)

def phase_html_structure(ctx: PipelineContext):
    setup_template_vars(ctx)
    final_html = ctx.task.step_results.get(STEP_FINAL_EDIT, {}).get("result", "")
    
    template_ref = ""
    if ctx.template_vars.get("site_template_html"):
        template_ref = (
            f"\n\n[SITE TEMPLATE REFERENCE]\n"
            f"Template Name: {ctx.template_vars.get('site_template_name', 'N/A')}\n"
            f"The generated content will be inserted into this template via {{{{content}}}} placeholder.\n"
            f"Adapt your HTML structure to be compatible with this template:\n"
            f"{ctx.template_vars['site_template_html']}"
        )
        
    html_struct_context = (
        f"Article HTML:\n{final_html}\n\n"
        f"Keyword: {ctx.task.main_keyword}\n"
        f"Language: {ctx.task.language}"
        f"{template_ref}"
    )
    add_log(ctx.db, ctx.task, "Starting HTML Structure formatting...", step=STEP_HTML_STRUCT)
    save_step_result(ctx.db, ctx.task, STEP_HTML_STRUCT, result=None, status="running")
    structured_html, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "html_structure", html_struct_context, variables=ctx.template_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"HTML Structure completed ({len(structured_html)} chars)", step=STEP_HTML_STRUCT)
    save_step_result(ctx.db, ctx.task, STEP_HTML_STRUCT, result=structured_html, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_content_fact_check(ctx: PipelineContext):
    if not settings.FACT_CHECK_ENABLED:
        return
        
    setup_template_vars(ctx)
    final_html = ctx.task.step_results.get(STEP_FINAL_EDIT, {}).get("result", "")
    
    ctx.template_vars["final_article"] = final_html
    ctx.template_vars["scraped_competitors_text"] = ctx.task.competitors_text[:15000] if ctx.task.competitors_text else ""
    
    fact_check_context = (
        f"Final Article HTML:\n{final_html}\n\n"
        f"Keyword: {ctx.task.main_keyword}\n"
        f"Language: {ctx.task.language}\n"
        f"Country: {ctx.task.country}"
    )
    
    add_log(ctx.db, ctx.task, "Starting Fact-Checking...", step=STEP_CONTENT_FACT_CHECK)
    save_step_result(ctx.db, ctx.task, STEP_CONTENT_FACT_CHECK, result=None, status="running")
    
    try:
        fact_check_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "fact_checking", fact_check_context,
            response_format={"type": "json_object"}, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
        
        add_log(ctx.db, ctx.task, f"Fact-Checking completed", step=STEP_CONTENT_FACT_CHECK)
        save_step_result(ctx.db, ctx.task, STEP_CONTENT_FACT_CHECK, result=fact_check_json_str, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)
    except Exception as e:
        add_log(ctx.db, ctx.task, f"Fact-checking agent failed or not found: {str(e)}", level="warn", step=STEP_CONTENT_FACT_CHECK)
        save_step_result(ctx.db, ctx.task, STEP_CONTENT_FACT_CHECK, result='{"verification_status": "warn", "issues": [], "summary": "Failed to run fact_checking agent."}', status="completed")

def phase_meta_generation(ctx: PipelineContext):
    setup_template_vars(ctx)
    structured_html = ctx.task.step_results.get(STEP_HTML_STRUCT, {}).get("result", "")
    meta_context = f"Article HTML:\n{structured_html}"
    add_log(ctx.db, ctx.task, "Generating Meta Tags (JSON)...", step=STEP_META_GEN)
    save_step_result(ctx.db, ctx.task, STEP_META_GEN, result=None, status="running")
    meta_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, "meta_generation", meta_context,
        response_format={"type": "json_object"}, variables=ctx.template_vars
    )
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    add_log(ctx.db, ctx.task, f"Meta Tags Generation completed", step=STEP_META_GEN)
    save_step_result(ctx.db, ctx.task, STEP_META_GEN, result=meta_json_str, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def run_pipeline(db: Session, task_id: str):
    ctx = PipelineContext(db, task_id)

    ctx.task.status = "processing"
    
    if ctx.task.total_cost is None:
        ctx.task.total_cost = 0.0
        
    db.commit()
    
    add_log(db, ctx.task, "🚀 Pipeline started / resumed", step=None)

    try:
        if ctx.use_serp:
            run_phase(db, ctx.task, STEP_SERP, phase_serp, ctx)
            run_phase(db, ctx.task, STEP_SCRAPING, phase_scraping, ctx)
            run_phase(db, ctx.task, STEP_AI_ANALYSIS, phase_ai_structure, ctx)
            run_phase(db, ctx.task, STEP_CHUNK_ANALYSIS, phase_chunk_analysis, ctx)
            run_phase(db, ctx.task, STEP_COMP_STRUCTURE, phase_competitor_structure, ctx)
            run_phase(db, ctx.task, STEP_FINAL_ANALYSIS, phase_final_structure, ctx)
            run_phase(db, ctx.task, STEP_STRUCTURE_FACT_CHECK, phase_structure_fact_check, ctx)
        else:
            if not ctx.task.outline:
                ctx.task.serp_data = {}
                ctx.task.competitors_text = ""
                ctx.task.outline = {"final_outline": {"page_title": ctx.page_title, "sections": []}}
                ctx.outline_data = ctx.task.outline
                db.commit()

        run_phase(db, ctx.task, STEP_PRIMARY_GEN, phase_primary_gen, ctx)

        # TEST MODE BREAKPOINT
        if settings.TEST_MODE:
            step_results = ctx.task.step_results or {}
            if not step_results.get("test_mode_approved"):
                add_log(db, ctx.task, "🛑 TEST MODE: Pausing pipeline after Primary Generation. Waiting for manual approval.", step=None)
                
                updated = dict(step_results)
                updated["waiting_for_approval"] = True
                ctx.task.step_results = updated
                ctx.task.status = "processing" # Keep it processing or pending
                db.commit()
                return # Early exit! Pipeline will be re-triggered by the /approve endpoint

        if ctx.use_serp:
            run_phase(db, ctx.task, STEP_COMP_COMPARISON, phase_competitor_comparison, ctx)
            run_phase(db, ctx.task, STEP_READER_OPINION, phase_reader_opinion, ctx)
            run_phase(db, ctx.task, STEP_INTERLINK, phase_interlink, ctx)
            run_phase(db, ctx.task, STEP_IMPROVER, phase_improver, ctx)

        run_phase(db, ctx.task, STEP_FINAL_EDIT, phase_final_editing, ctx)
        
        if settings.FACT_CHECK_ENABLED:
            run_phase(db, ctx.task, STEP_CONTENT_FACT_CHECK, phase_content_fact_check, ctx)
            
        run_phase(db, ctx.task, STEP_HTML_STRUCT, phase_html_structure, ctx)
        run_phase(db, ctx.task, STEP_META_GEN, phase_meta_generation, ctx)

        # Assemble and SAVE
        try:
            add_log(db, ctx.task, "Starting article assembly and saving...", step=None)
            structured_html = ctx.task.step_results.get(STEP_HTML_STRUCT, {}).get("result", "")
            meta_json_str = ctx.task.step_results.get(STEP_META_GEN, {}).get("result", "{}")
            meta_data = clean_and_parse_json(meta_json_str)
            
            title = meta_data.get("title", f"{ctx.task.main_keyword} Guide")
            description = meta_data.get("description", "")
            if not title:
                title = ctx.task.main_keyword.title()
            if not description:
                description = f"Read our comprehensive guide about {ctx.task.main_keyword}."

            word_count = len(BeautifulSoup(structured_html, "html.parser").get_text(strip=True).split())
            full_page = generate_full_page(db, str(ctx.task.target_site_id), structured_html, title, description)

            # Process fact_check results
            fact_check_status_val = ""
            fact_check_issues_val = []
            needs_review_val = False
            
            if settings.FACT_CHECK_ENABLED:
                fc_res_str = ctx.task.step_results.get(STEP_CONTENT_FACT_CHECK, {}).get("result", "{}")
                if fc_res_str:
                    fc_data = clean_and_parse_json(fc_res_str)
                    if fc_data:
                        fact_check_status_val = fc_data.get("verification_status", "")
                        fact_check_issues_val = fc_data.get("issues", [])
                        
                        critical_count = sum(1 for issue in fact_check_issues_val if issue.get("severity") == "critical")
                        
                        if fact_check_status_val == "fail" or critical_count >= settings.FACT_CHECK_FAIL_THRESHOLD:
                            needs_review_val = True
                            add_log(db, ctx.task, f"Fact-check marked for review ({critical_count} critical issues).", level="warn", step=STEP_CONTENT_FACT_CHECK)
                            
                            if getattr(settings, "FACT_CHECK_MODE", "soft") == "strict":
                                raise Exception("Fact-check failed in strict mode. Task aborted.")
                        elif fact_check_status_val == "warn":
                            add_log(db, ctx.task, f"Fact-check returned warnings.", level="warn", step=STEP_CONTENT_FACT_CHECK)

            # Verify if an article exists already for this task
            existing = db.query(GeneratedArticle).filter(GeneratedArticle.task_id == ctx.task.id).first()
            if not existing:
                article = GeneratedArticle(
                    task_id=ctx.task.id,
                    title=title,
                    description=description,
                    html_content=structured_html,
                    full_page_html=full_page,
                    word_count=word_count,
                    fact_check_status=fact_check_status_val,
                    fact_check_issues=fact_check_issues_val,
                    needs_review=needs_review_val
                )
                db.add(article)

            if ctx.task.project_id:
                deduplicator = ContentDeduplicator(db)
                anchors = deduplicator.extract_anchors(
                    article_html=structured_html,
                    task_id=str(ctx.task.id),
                    keyword=ctx.task.main_keyword
                )
                deduplicator.save_anchors(project_id=str(ctx.task.project_id), task_id=str(ctx.task.id), anchors=anchors)
            
            # The last operation should be setting status and committing
            ctx.task.status = "completed"
            db.commit()
            
            add_log(db, ctx.task, "✅ Pipeline finished successfully", step=None)
            notify_task_success(str(ctx.task.id), ctx.task.main_keyword, ctx.site_name, word_count)
            
        except Exception as save_err:
            db.rollback()
            add_log(db, ctx.task, f"❌ Error saving article: {str(save_err)}", level="error", step=None)
            ctx.task.status = "failed"
            ctx.task.error_log = traceback.format_exc()
            db.commit()
            notify_task_failed(str(ctx.task.id), ctx.task.main_keyword, str(save_err), ctx.site_name)

    except Exception as e:
        db.rollback() # VERY IMPORTANT: reset session to allow updating error status
        # Mark any running step as failed
        if ctx.task.step_results:
            updated_steps = dict(ctx.task.step_results)
            for step_key, step_val in updated_steps.items():
                if isinstance(step_val, dict) and step_val.get("status") == "running":
                    step_val["status"] = "failed"
                    step_val["error"] = str(e)[:2000]
            ctx.task.step_results = updated_steps
        
        ctx.task.status = "failed"
        ctx.task.error_log = traceback.format_exc()
        db.commit()
        add_log(db, ctx.task, f"❌ Pipeline failed: {str(e)}", level="error", step=None)
        notify_task_failed(str(ctx.task.id), ctx.task.main_keyword, str(e), ctx.site_name)
