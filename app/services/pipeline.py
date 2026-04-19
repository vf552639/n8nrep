import json
import traceback
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup, Comment

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
from app.services.prompt_llm_kwargs import (
    llm_sampling_kwargs_from_prompt,
    format_llm_params_log_line,
)
from app.services.template_engine import generate_full_page, get_template_for_reference
from app.services.legal_reference import inject_legal_template_vars
from app.services.notifier import notify_task_success, notify_task_failed
from app.services.deduplication import ContentDeduplicator
from app.config import settings

from app.services.json_parser import clean_and_parse_json
from app.services.meta_parser import extract_meta_from_parsed
from app.services.pipeline_constants import *
from app.services.pipeline_presets import (
    PIPELINE_PRESETS,
    pipeline_steps_use_serp,
    resolve_pipeline_steps,
)
from app.services.word_counter import count_content_words
from app.services.html_inserter import programmatic_html_insert
import re
import datetime
import signal

class PipelineContext:
    def __init__(self, db: Session, task_id: str, auto_mode: bool = False):
        self.db = db
        self.task_id = task_id
        self.auto_mode = auto_mode
        
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
        self.pipeline_steps = None

        if self.task.blueprint_page_id:
            self.blueprint_page = (
                db.query(BlueprintPage).filter(BlueprintPage.id == self.task.blueprint_page_id).first()
            )
            if self.blueprint_page:
                self.page_slug = self.blueprint_page.page_slug
                self.page_title = self.blueprint_page.page_title
                self.pipeline_steps = resolve_pipeline_steps(self.blueprint_page)
                self.use_serp = pipeline_steps_use_serp(self.pipeline_steps)

                bid = self.blueprint_page.blueprint_id
                all_pages_db = (
                    db.query(BlueprintPage)
                    .filter(BlueprintPage.blueprint_id == bid)
                    .order_by(BlueprintPage.sort_order)
                    .all()
                )
                self.all_site_pages = [
                    {"slug": p.page_slug, "title": p.page_title, "type": p.page_type, "url": p.filename}
                    for p in all_pages_db
                ]
                    
        self.analysis_vars = {}
        self.template_vars = {}
        self.outline_data = self.task.outline or {}

def get_prompt_obj(db: Session, agent_name: str) -> Prompt:
    prompt_obj = db.query(Prompt).filter(Prompt.agent_name == agent_name, Prompt.is_active == True).first()
    if not prompt_obj and agent_name == "content_fact_checking":
        prompt_obj = db.query(Prompt).filter(Prompt.agent_name == "fact_checking", Prompt.is_active == True).first()
    if not prompt_obj:
        raise Exception(f"No active prompt found for agent: {agent_name}")
    return prompt_obj

def save_step_result(db: Session, task: Task, step_name: str, result: str, model: str = None, status: str = "completed", cost: float = 0.0, variables_snapshot: dict = None, resolved_prompts: dict = None, exclude_words_violations: dict = None, input_word_count: int = None, output_word_count: int = None, word_count_warning: bool = None, word_loss_percentage: float = None):
    if task.step_results is None:
        task.step_results = {}
    
    now_iso = datetime.datetime.utcnow().isoformat()
    previous_step = (task.step_results or {}).get(step_name, {}) if isinstance(task.step_results, dict) else {}
    step_data = {
        "status": status,
        "result": result[:50000] if result else None,
        "timestamp": now_iso,
    }
    if status == "running":
        step_data["started_at"] = previous_step.get("started_at") or now_iso
    elif previous_step.get("started_at"):
        step_data["started_at"] = previous_step.get("started_at")
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
    if input_word_count is not None:
        step_data["input_word_count"] = input_word_count
    if output_word_count is not None:
        step_data["output_word_count"] = output_word_count
    if word_count_warning is not None:
        step_data["word_count_warning"] = word_count_warning
    if word_loss_percentage is not None:
        step_data["word_loss_percentage"] = word_loss_percentage
    
    updated = dict(task.step_results)
    updated[step_name] = step_data
    task.step_results = updated
    task.last_heartbeat = datetime.datetime.utcnow()
    db.commit() # Required to trigger SQLAlchemy JSON updates safely without flag_modified

def mark_step_running(db: Session, task: Task, step_key: str, model_name: str = None):
    """Mark pipeline step as running and preserve original started_at."""
    save_step_result(
        db,
        task,
        step_key,
        result=None,
        status="running",
        model=model_name,
    )

def add_log(db: Session, task: Task, msg: str, level: str = "info", step: str = None):
    entry = {
        "ts": datetime.datetime.utcnow().isoformat(),
        "level": level,
        "msg": msg,
    }
    if step:
        entry["step"] = step
    
    current_logs = list(task.log_events or [])
    current_logs.append(entry)
    task.log_events = current_logs[-500:]
    db.commit()


def _completed_step_body(task: Task, step_key: str) -> str:
    sr = task.step_results or {}
    block = sr.get(step_key, {})
    if not isinstance(block, dict):
        return ""
    st = block.get("status")
    if st not in ("completed", "completed_with_warnings"):
        return ""
    return str(block.get("result") or "").strip()


def pick_structured_html_for_assembly(ctx: PipelineContext) -> str:
    order = [
        STEP_IMAGE_INJECT,
        STEP_HTML_STRUCT,
        STEP_FINAL_EDIT,
        STEP_IMPROVER,
        STEP_INTERLINK,
        STEP_READER_OPINION,
        STEP_COMP_COMPARISON,
        STEP_PRIMARY_GEN,
        STEP_PRIMARY_GEN_ABOUT,
        STEP_PRIMARY_GEN_LEGAL,
    ]
    for key in order:
        body = _completed_step_body(ctx.task, key)
        if body:
            return body
    return ""


def pick_html_for_meta(ctx: PipelineContext) -> str:
    order = [
        STEP_HTML_STRUCT,
        STEP_FINAL_EDIT,
        STEP_IMPROVER,
        STEP_PRIMARY_GEN,
        STEP_PRIMARY_GEN_ABOUT,
        STEP_PRIMARY_GEN_LEGAL,
    ]
    for key in order:
        body = _completed_step_body(ctx.task, key)
        if body:
            return body
    return ""


from typing import Optional, Tuple

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
        allow_empty_critical = CRITICAL_VARS_ALLOW_EMPTY.get(agent_name, frozenset())
        missing_critical = []
        for cv in critical:
            if cv in all_unresolved:
                missing_critical.append(cv)
            elif cv in all_empty and cv not in allow_empty_critical:
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
    
    if user_template:
        ctx_text = (context or "").strip()
        if ctx_text:
            user_msg = f"{user_template}\n\n[CONTEXT]\n{context}"
        else:
            user_msg = user_template
    else:
        user_msg = context or ""
    
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
    est_tokens = total_chars // 4
    if est_tokens > 50000:
        add_log(
            ctx.db,
            ctx.task,
            f"Large context for {agent_name}: ~{est_tokens} tokens estimated",
            level="warn",
            step=agent_name,
        )
    
    sampling = llm_sampling_kwargs_from_prompt(prompt)
    kwargs = {
        "system_prompt": system_text,
        "user_prompt": user_msg,
        "model": prompt.model,
        **sampling,
    }
    if response_format:
        kwargs["response_format"] = response_format

    def _touch_heartbeat():
        ctx.task.last_heartbeat = datetime.datetime.utcnow()
        ctx.db.commit()

    def _on_llm_progress(event: str, payload: dict):
        if event == "retry_wait":
            add_log(
                ctx.db,
                ctx.task,
                (
                    f"[{agent_name}] Retry {payload.get('attempt')}/{payload.get('max_retries')}: "
                    f"{payload.get('reason')}. Sleeping {payload.get('sleep_seconds')}s"
                ),
                level="warn",
                step=agent_name,
            )
            _touch_heartbeat()
        elif event == "response_received":
            usage = payload.get("usage") or {}
            p = usage.get("prompt_tokens", 0)
            c = usage.get("completion_tokens", 0)
            cached = usage.get("cached_tokens", 0)
            reasoning = usage.get("reasoning_tokens", 0)

            tokens_msg = f"{p}+{c} tokens"
            if cached > 0:
                tokens_msg += f" | ⚡ {cached} cached"
            if reasoning > 0:
                tokens_msg += f" | 🧠 {reasoning} reasoning"

            add_log(
                ctx.db,
                ctx.task,
                (
                    f"[{agent_name}] LLM response received "
                    f"({tokens_msg}, ${float(payload.get('cost') or 0.0):.5f})"
                ),
                level="info",
                step=agent_name,
            )
            _touch_heartbeat()

    add_log(
        ctx.db,
        ctx.task,
        format_llm_params_log_line(agent_name, prompt, kwargs),
        level="info",
        step=agent_name,
    )
    _touch_heartbeat()
    kwargs["timeout"] = int(getattr(settings, "LLM_REQUEST_TIMEOUT", 300))
    kwargs["progress_callback"] = _on_llm_progress

    res, cost, model, _ = generate_text(**kwargs)
    return res, cost, model, resolved_prompts, variables_snapshot

def call_agent_with_exclude_validation(
    ctx: PipelineContext,
    agent_name: str,
    context: str,
    step_constant: str,
    max_retries: Optional[int] = None,
):
    from app.services.exclude_words_validator import ExcludeWordsValidator

    if max_retries is None:
        max_retries = getattr(settings, "SELF_CHECK_MAX_RETRIES", 1)
    retry_budget = float(getattr(settings, "SELF_CHECK_MAX_COST_PER_STEP", 0.10) or 0.0)
    retry_spent = 0.0

    result_text, total_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, agent_name, context, variables=ctx.template_vars
    )

    exclude_str = ctx.template_vars.get("exclude_words", "")
    if not exclude_str.strip():
        return result_text, total_cost, actual_model, resolved_prompts, variables_snapshot, None

    validator = ExcludeWordsValidator(exclude_str)
    report = validator.validate(result_text)

    if report["passed"]:
        return result_text, total_cost, actual_model, resolved_prompts, variables_snapshot, None

    add_log(
        ctx.db,
        ctx.task,
        f"EXCLUDE_WORDS violation: found {report['found_words']}",
        level="warn",
        step=step_constant,
    )

    retry_count = 0
    while retry_count < max_retries and not report["passed"]:
        if retry_budget > 0 and retry_spent >= retry_budget:
            add_log(
                ctx.db,
                ctx.task,
                f"Budget limit reached for exclude-word retries (${retry_spent:.4f}). Using best result.",
                level="warn",
                step=step_constant,
            )
            break
        retry_count += 1
        add_log(
            ctx.db,
            ctx.task,
            f"Retrying agent {agent_name} due to exclude words violation (Attempt {retry_count}).",
            level="info",
            step=step_constant,
        )

        retry_context = context + (
            f"\n\nCRITICAL: Your previous output contained forbidden words: {report['found_words']}. "
            f"You MUST NOT use these words. Rewrite the text avoiding them completely."
        )

        retry_text, retry_cost, r_model, r_prompts, r_vars = call_agent(
            ctx, agent_name, retry_context, variables=ctx.template_vars
        )
        retry_spent += retry_cost
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
            for t in _safe_list(scraping_result.get("scraped_titles"))
            if isinstance(t, str) and t.strip()
        ]
        scraped_descriptions = [
            d.strip()
            for d in _safe_list(scraping_result.get("scraped_descriptions"))
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

        # Auto-generate additional_keywords from SERP data if task field is empty
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
            "people_also_search": json.dumps(_safe_list(serp.get("people_also_search")), ensure_ascii=False),
        }

        # Ensure additional_keywords is never empty for critical agents:
        # if SERP data and manual field are both empty, fall back to main keyword.
        if not ctx.analysis_vars.get("additional_keywords"):
            ctx.analysis_vars["additional_keywords"] = ctx.task.main_keyword

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
        "additional_keywords": ctx.task.additional_keywords or ctx.analysis_vars.get("additional_keywords", ""),
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
        "people_also_search": ctx.analysis_vars.get("people_also_search", ""),
        "structure_fact_checking": ""
    }

    # Completed pipeline steps → {{result_<step_key>}} (only if variable missing or empty)
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

    # Fetch HTML template reference for LLM injection (optional per-project)
    use_template = True
    if ctx.task.project_id:
        project = (
            ctx.db.query(SiteProject)
            .filter(SiteProject.id == ctx.task.project_id)
            .first()
        )
        if project and not getattr(project, "use_site_template", True):
            use_template = False

    if use_template:
        site_template_html, site_template_name = get_template_for_reference(
            ctx.db, str(ctx.task.target_site_id)
        )
        ctx.template_vars["site_template_html"] = site_template_html or ""
        ctx.template_vars["site_template_name"] = site_template_name or ""
    else:
        ctx.template_vars["site_template_html"] = ""
        ctx.template_vars["site_template_name"] = ""

    inject_legal_template_vars(ctx)

def run_phase(db: Session, task: Task, step_key: str, phase_func, *args, **kwargs):
    """Wrapper that skips phase_func if already completed."""
    if task.step_results and step_key in task.step_results:
        if task.step_results[step_key].get("status") == "completed":
            print(f"Skipping {step_key} - already completed")
            return
            
    print(f"Running phase: {step_key}")
    task.last_heartbeat = datetime.datetime.utcnow()
    db.commit()
    timeout_seconds = int(getattr(settings, "STEP_TIMEOUT_MINUTES", 15)) * 60
    old_handler = None
    alarm_enabled = False
    try:
        if hasattr(signal, "SIGALRM"):
            def _handle_step_timeout(signum, frame):
                raise TimeoutError(f"Step timed out after {timeout_seconds}s")
            try:
                old_handler = signal.getsignal(signal.SIGALRM)
                signal.signal(signal.SIGALRM, _handle_step_timeout)
                signal.alarm(timeout_seconds)
                alarm_enabled = True
            except ValueError:
                # SIGALRM is only valid in main thread on some runtimes.
                alarm_enabled = False
        phase_func(*args, **kwargs)
    except TimeoutError as e:
        msg = str(e)
        save_step_result(db, task, step_key, result=msg, status="failed")
        add_log(db, task, f"{step_key} failed: {msg}", level="error", step=step_key)
        raise
    finally:
        if alarm_enabled and hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)

def phase_serp(ctx: PipelineContext):
    if not ctx.task.serp_data:
        add_log(ctx.db, ctx.task, "Fetching SERP data...", step=STEP_SERP)
        mark_step_running(ctx.db, ctx.task, STEP_SERP)
        try:
            serp_data = fetch_serp_data(
                ctx.task.main_keyword,
                ctx.task.country,
                ctx.task.language,
                serp_config=ctx.task.serp_config,
            )
        except Exception as serp_err:
            add_log(
                ctx.db,
                ctx.task,
                f"❌ SERP fetch failed: {str(serp_err)}",
                level="error",
                step=STEP_SERP,
            )
            save_step_result(
                ctx.db,
                ctx.task,
                STEP_SERP,
                result=json.dumps({"error": str(serp_err)}),
                status="failed",
            )
            raise
        ctx.task.serp_data = serp_data
        ctx.db.commit()
        add_log(ctx.db, ctx.task, f"SERP Research completed.", step=STEP_SERP)
        # Save summary for step_result (full data in task.serp_data)
        def _safe_len(val) -> int:
            return len(val) if isinstance(val, list) else 0

        serp_summary = {
            "source": serp_data.get("source", "unknown") if isinstance(serp_data, dict) else "unknown",
            "_from_cache": bool(serp_data.get("_from_cache")) if isinstance(serp_data, dict) else False,
            "urls_count": _safe_len(serp_data.get("urls")) if isinstance(serp_data, dict) else 0,
            "organic_count": _safe_len(serp_data.get("organic_results")) if isinstance(serp_data, dict) else 0,
            "paa_count": _safe_len(serp_data.get("paa_full")) if isinstance(serp_data, dict) else 0,
            "related_count": _safe_len(serp_data.get("related_searches")) if isinstance(serp_data, dict) else 0,
            "has_featured_snippet": serp_data.get("featured_snippet") is not None if isinstance(serp_data, dict) else False,
            "has_knowledge_graph": serp_data.get("knowledge_graph") is not None if isinstance(serp_data, dict) else False,
            "has_ai_overview": serp_data.get("ai_overview") is not None if isinstance(serp_data, dict) else False,
            "has_answer_box": serp_data.get("answer_box") is not None if isinstance(serp_data, dict) else False,
            "ads_count": serp_data.get("search_intent_signals", {}).get("ads_count", 0) if isinstance(serp_data, dict) else 0,
            "people_also_search_count": _safe_len(serp_data.get("people_also_search")) if isinstance(serp_data, dict) else 0,
            "people_also_search": _safe_list(serp_data.get("people_also_search")) if isinstance(serp_data, dict) else [],
            "serp_features": _safe_list(serp_data.get("serp_features")) if isinstance(serp_data, dict) else [],
            "urls": _safe_list(serp_data.get("urls")) if isinstance(serp_data, dict) else [],
        }
        if isinstance(serp_data, dict) and serp_data.get("source") == "google+bing":
            serp_summary["google_data"] = serp_data.get("google_data")
            serp_summary["bing_data"] = serp_data.get("bing_data")
        save_step_result(ctx.db, ctx.task, STEP_SERP, result=json.dumps(serp_summary, ensure_ascii=False), status="completed")
        if not ctx.auto_mode:
            step_results = dict(ctx.task.step_results or {})
            step_results["_pipeline_pause"] = {"active": True, "reason": "serp_review"}
            ctx.task.step_results = step_results
            ctx.task.status = "paused"
            ctx.db.commit()
            add_log(
                ctx.db,
                ctx.task,
                "⏸️ Pipeline paused: waiting for SERP URLs review",
                step=STEP_SERP,
            )

def phase_scraping(ctx: PipelineContext):
    if not ctx.task.competitors_text:
        serp_data = ctx.task.serp_data if isinstance(ctx.task.serp_data, dict) else {}
        urls = serp_data.get("urls", [])
        if not urls:
            serp_source = serp_data.get("source", "unknown")
            add_log(ctx.db, ctx.task, 
                    f"❌ No organic URLs in SERP data (source={serp_source}) — pipeline stopped. "
                    "Check SERP step logs for debug info.", 
                    level="error", step=STEP_SCRAPING)
            save_step_result(ctx.db, ctx.task, STEP_SCRAPING, 
                             result=json.dumps({"error": "No organic URLs", "serp_source": serp_source}), 
                             status="failed")
            raise Exception(f"Pipeline stopped: SERP returned 0 organic URLs (source={serp_source}). Cannot proceed without competitor data.")
        
        add_log(ctx.db, ctx.task, f"Scraping {len(urls)} competitors...", step=STEP_SCRAPING)
        mark_step_running(ctx.db, ctx.task, STEP_SCRAPING)
    
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
            "scraped_titles": scrape_data.get("scraped_titles", []),
            "scraped_descriptions": scrape_data.get("scraped_descriptions", []),
            "titles_source": "scraping",
            "descriptions_source": "scraping",
            "failed_results": scrape_data.get("failed_results", []),
            "serper_count": scrape_data.get("serper_count", 0),
            "direct_count": scrape_data.get("direct_count", 0),
            "cache_hits": scrape_data.get("cache_hits", 0),
            "cache_misses": scrape_data.get("cache_misses", 0),
        }

        add_log(ctx.db, ctx.task, f"Scraped competitors. Avg word count: {scrape_data['average_word_count']}", step=STEP_SCRAPING)
        save_step_result(ctx.db, ctx.task, STEP_SCRAPING, result=json.dumps(scrape_summary, ensure_ascii=False), status="completed")

def phase_ai_structure(ctx: PipelineContext):
    ctx.db.refresh(ctx.task)  # Force reload from DB
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting AI Structure Analysis...", step=STEP_AI_ANALYSIS)
    mark_step_running(ctx.db, ctx.task, STEP_AI_ANALYSIS)
    ai_structure, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, "ai_structure_analysis", ctx.base_context, 
        response_format={"type": "json_object"}, variables=ctx.analysis_vars
    )
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    ctx.analysis_vars["result_ai_structure_analysis"] = ai_structure
    ctx.outline_data["ai_structure"] = ai_structure
    
    add_log(ctx.db, ctx.task, f"ai_structure raw (first 500): {ai_structure[:500]}", level="debug", step=STEP_AI_ANALYSIS)
    
    ai_struct_data = clean_and_parse_json(
        ai_structure,
        unwrap_keys={"intent", "Taxonomy", "Attention", "structura"},
    )
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
    mark_step_running(ctx.db, ctx.task, STEP_CHUNK_ANALYSIS)
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
    mark_step_running(ctx.db, ctx.task, STEP_COMP_STRUCTURE)
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
    mark_step_running(ctx.db, ctx.task, STEP_FINAL_ANALYSIS)
    
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
    mark_step_running(ctx.db, ctx.task, STEP_STRUCTURE_FACT_CHECK)
    
    fact_check_report, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "structure_fact_checking", "", variables=ctx.template_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Structure Fact-Checking completed ({len(fact_check_report)} chars)", step=STEP_STRUCTURE_FACT_CHECK)
    save_step_result(ctx.db, ctx.task, STEP_STRUCTURE_FACT_CHECK, result=fact_check_report, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_image_prompt_gen(ctx: PipelineContext):
    """LLM agent builds image prompts per multimedia block using template vars."""
    if not settings.IMAGE_GEN_ENABLED:
        add_log(ctx.db, ctx.task, "Image generation disabled globally — skipping", step=STEP_IMAGE_PROMPT_GEN)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_PROMPT_GEN, result=json.dumps({"images": [], "skipped": True}), status="completed")
        return

    from app.services.image_utils import (
        _extract_multimedia_from_text_content,
        extract_multimedia_blocks,
    )

    outline_raw = ctx.task.step_results.get(STEP_FINAL_ANALYSIS, {}).get("result", "")
    if not outline_raw:
        add_log(ctx.db, ctx.task, "No final structure found — skipping image prompt gen", step=STEP_IMAGE_PROMPT_GEN)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_PROMPT_GEN, result=json.dumps({"images": []}), status="completed")
        return

    outline_json = clean_and_parse_json(outline_raw)
    multimedia_blocks = extract_multimedia_blocks(outline_json)

    outline_raw_str = str(outline_raw)
    if not multimedia_blocks and outline_raw_str and len(outline_raw_str) > 100:
        text_blocks = _extract_multimedia_from_text_content(outline_raw_str, "outline_raw")
        if text_blocks:
            for i, tb in enumerate(text_blocks, start=1):
                tb["id"] = f"img_{i}"
            multimedia_blocks = text_blocks
            add_log(
                ctx.db,
                ctx.task,
                f"Found {len(text_blocks)} MULTIMEDIA block(s) via raw text fallback "
                f"(not in JSON keys)",
                level="info",
                step=STEP_IMAGE_PROMPT_GEN,
            )

    if not multimedia_blocks:
        outline_snippet = outline_raw_str[:1500] if outline_raw_str else "EMPTY"
        add_log(
            ctx.db,
            ctx.task,
            f"[DEBUG] No MULTIMEDIA found anywhere. "
            f"Outline snippet (first 1500 chars): {outline_snippet}",
            level="warn",
            step=STEP_IMAGE_PROMPT_GEN,
        )
        add_log(
            ctx.db,
            ctx.task,
            "⚠️ No MULTIMEDIA blocks in outline. Возможные причины: "
            "1) промпт final_structure_analysis не генерирует поле MULTIMEDIA/multimedia в секциях; "
            "2) несоответствие регистра ключа в JSON. "
            "Проверь step_results['final_structure_analysis'] вручную.",
            level="warn",
            step=STEP_IMAGE_PROMPT_GEN,
        )
        add_log(ctx.db, ctx.task, "No MULTIMEDIA blocks found in outline — skipping", step=STEP_IMAGE_PROMPT_GEN)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_PROMPT_GEN, result=json.dumps({"images": []}), status="completed")
        return

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

    def _norm_mm_type(block: dict) -> str:
        mm = block.get("multimedia", {}) if isinstance(block, dict) else {}
        t = mm.get("Type") or mm.get("type") or ""
        t_clean = str(t).strip().lower()
        return TYPE_NORMALIZE_MAP.get(t_clean, "")

    def _extract_prompt_fallback(data) -> str:
        """Extract an image prompt from LLM JSON (known keys, long strings, or nested dicts)."""
        if not isinstance(data, dict):
            return ""
        for key in (
            "image_prompt",
            "midjourney_prompt",
            "prompt",
            "mj_prompt",
            "visual_prompt",
            "description",
        ):
            val = data.get(key)
            if val and isinstance(val, str) and len(val.strip()) > 20:
                return val.strip()
        for _, val in data.items():
            if isinstance(val, str) and len(val.strip()) > 50:
                return val.strip()
        for _, val in data.items():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        nested = _extract_prompt_fallback(item)
                        if nested:
                            return nested
        for _, val in data.items():
            if isinstance(val, dict):
                nested = _extract_prompt_fallback(val)
                if nested:
                    return nested
        return ""

    generatable_types = {"Image", "Infographic"}
    normalized_types = [(_norm_mm_type(b) or "Image") for b in multimedia_blocks]
    eligible_blocks = [
        b for b in multimedia_blocks
        if (_norm_mm_type(b) or "Image") in generatable_types
    ]
    skipped_count = len(multimedia_blocks) - len(eligible_blocks)
    add_log(
        ctx.db,
        ctx.task,
        f"Outline parsed. Total MULTIMEDIA blocks found: {len(multimedia_blocks)}. "
        f"Eligible (Image/Infographic): {len(eligible_blocks)}, skipped (other types): {skipped_count}. "
        f"Types found: {normalized_types}",
        step=STEP_IMAGE_PROMPT_GEN,
    )
    if not eligible_blocks:
        add_log(
            ctx.db,
            ctx.task,
            "MULTIMEDIA blocks found, but no generatable types (Image/Infographic) — skipping",
            step=STEP_IMAGE_PROMPT_GEN,
        )
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_PROMPT_GEN, result=json.dumps({"images": []}), status="completed")
        return

    add_log(
        ctx.db,
        ctx.task,
        f"Found {len(multimedia_blocks)} MULTIMEDIA blocks, eligible: {len(eligible_blocks)}, skipped: {skipped_count}. Generating prompts...",
        step=STEP_IMAGE_PROMPT_GEN,
    )
    mark_step_running(ctx.db, ctx.task, STEP_IMAGE_PROMPT_GEN)

    setup_template_vars(ctx)
    images = []
    total_cost = 0.0
    actual_model = None
    last_resolved_prompts = None
    last_variables_snapshot = None

    for idx, block in enumerate(eligible_blocks, start=1):
        mm = block.get("multimedia", {}) if isinstance(block, dict) else {}
        mm_type = _norm_mm_type(block) or "Image"
        description = str(mm.get("Description") or mm.get("description") or "").strip()
        purpose = str(mm.get("Purpose") or mm.get("purpose") or "").strip()
        location = str(mm.get("Location") or mm.get("location") or "").strip() or f"image_{idx}"
        parent_title = str(block.get("section") or "").strip() or "Untitled Section"

        block_vars = dict(ctx.template_vars or {})
        block_vars.update(
            {
                "type": mm_type,
                "description": description,
                "purpose": purpose,
                "parent_title": parent_title,
                "location": location,
            }
        )

        block_context = (
            "MULTIMEDIA block payload:\n"
            f"{json.dumps(block, ensure_ascii=False, indent=2)}"
        )

        try:
            block_result_json, block_cost, block_model, block_resolved_prompts, block_variables_snapshot = call_agent(
                ctx,
                "image_prompt_generation",
                block_context,
                response_format={"type": "json_object"},
                variables=block_vars,
            )
            total_cost += block_cost
            actual_model = block_model
            last_resolved_prompts = block_resolved_prompts
            last_variables_snapshot = block_variables_snapshot

            parsed = clean_and_parse_json(block_result_json)
            if not isinstance(parsed, dict):
                parsed = {}

            midjourney_prompt = _extract_prompt_fallback(parsed)
            if not midjourney_prompt:
                raw_snip = str(block_result_json)[:500]
                add_log(
                    ctx.db,
                    ctx.task,
                    f"[DEBUG] Image prompt raw response for {block.get('id', f'img_{idx}')}: {raw_snip}",
                    level="warn",
                    step=STEP_IMAGE_PROMPT_GEN,
                )
                add_log(
                    ctx.db,
                    ctx.task,
                    f"Image prompt gen returned empty prompt for block {block.get('id', f'img_{idx}')}; block skipped",
                    level="warn",
                    step=STEP_IMAGE_PROMPT_GEN,
                )
                continue

            mj = str(midjourney_prompt).strip()
            images.append(
                {
                    "id": block.get("id", f"img_{idx}"),
                    "section": parent_title,
                    "location": location,
                    "type": mm_type,
                    "description": description,
                    "purpose": purpose,
                    "image_prompt": mj,
                    "midjourney_prompt": mj,
                    "alt_text": str(parsed.get("alt_text") or f"{mm_type} for {parent_title}").strip(),
                    "aspect_ratio": str(parsed.get("aspect_ratio") or "16:9").strip(),
                }
            )
        except Exception as e:
            add_log(
                ctx.db,
                ctx.task,
                f"Failed image prompt generation for block {block.get('id', f'img_{idx}')}: {e}",
                level="error",
                step=STEP_IMAGE_PROMPT_GEN,
            )

    if len(images) == 0 and len(eligible_blocks) > 0:
        add_log(
            ctx.db,
            ctx.task,
            "No prompts built in primary pass. Running simplified fallback prompt extraction...",
            level="warn",
            step=STEP_IMAGE_PROMPT_GEN,
        )
        for idx, block in enumerate(eligible_blocks, start=1):
            mm = block.get("multimedia", {}) if isinstance(block, dict) else {}
            mm_type = _norm_mm_type(block) or "Image"
            description = str(mm.get("Description") or mm.get("description") or "").strip()
            parent_title = str(block.get("section") or "").strip() or "Untitled Section"
            purpose = str(mm.get("Purpose") or mm.get("purpose") or "").strip()
            location = str(mm.get("Location") or mm.get("location") or "").strip() or f"image_{idx}"
            if not description:
                description = f"{mm_type} for section '{parent_title}'"

            fallback_context = (
                f"Create an AI image generation prompt for: {description}. "
                "Respond ONLY with JSON: "
                '{"image_prompt": "<detailed English prompt>", '
                '"alt_text": "<short alt text>", "aspect_ratio": "16:9"}'
            )
            try:
                fallback_json, fb_cost, fb_model, fb_resolved_prompts, fb_variables_snapshot = call_agent(
                    ctx,
                    "image_prompt_generation",
                    fallback_context,
                    response_format={"type": "json_object"},
                    variables=ctx.template_vars,
                )
                total_cost += fb_cost
                actual_model = fb_model
                last_resolved_prompts = fb_resolved_prompts
                last_variables_snapshot = fb_variables_snapshot

                parsed_fb = clean_and_parse_json(fallback_json)
                if not isinstance(parsed_fb, dict):
                    parsed_fb = {}
                fallback_prompt = _extract_prompt_fallback(parsed_fb)
                if not fallback_prompt:
                    add_log(
                        ctx.db,
                        ctx.task,
                        f"Fallback empty prompt for block {block.get('id', f'img_{idx}')}. Raw: {str(fallback_json)[:500]}",
                        level="warn",
                        step=STEP_IMAGE_PROMPT_GEN,
                    )
                    continue

                fb = str(fallback_prompt).strip()
                images.append(
                    {
                        "id": block.get("id", f"img_{idx}"),
                        "section": parent_title,
                        "location": location,
                        "type": mm_type,
                        "description": description,
                        "purpose": purpose,
                        "image_prompt": fb,
                        "midjourney_prompt": fb,
                        "alt_text": str(parsed_fb.get("alt_text") or f"{mm_type} for {parent_title}").strip(),
                        "aspect_ratio": str(parsed_fb.get("aspect_ratio") or "16:9").strip(),
                    }
                )
            except Exception as e:
                add_log(
                    ctx.db,
                    ctx.task,
                    f"Fallback image prompt generation failed for block {block.get('id', f'img_{idx}')}: {e}",
                    level="error",
                    step=STEP_IMAGE_PROMPT_GEN,
                )

    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + total_cost
    result_json = json.dumps({"images": images}, ensure_ascii=False)

    add_log(ctx.db, ctx.task, f"Image prompt generation completed: {len(images)} prompts built", step=STEP_IMAGE_PROMPT_GEN)
    save_step_result(
        ctx.db,
        ctx.task,
        STEP_IMAGE_PROMPT_GEN,
        result=result_json,
        model=actual_model,
        status="completed",
        cost=total_cost,
        variables_snapshot=last_variables_snapshot,
        resolved_prompts=last_resolved_prompts,
    )


def phase_image_gen(ctx: PipelineContext):
    """Service step: OpenRouter image models (sync), upload to ImgBB."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from app.services.image_generator import ImageResult, OpenRouterImageGenerator, resolve_image_generation_model
    from app.services.image_hosting import ImgBBUploader

    if not settings.IMAGE_GEN_ENABLED:
        add_log(ctx.db, ctx.task, "Image generation disabled — skipping", step=STEP_IMAGE_GEN)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_GEN, result=json.dumps({"images": [], "skipped": True}), status="completed")
        return
    if not settings.OPENROUTER_API_KEY:
        add_log(
            ctx.db,
            ctx.task,
            "❌ OPENROUTER_API_KEY не задан — image generation невозможен. Тот же ключ, что для LLM.",
            level="error",
            step=STEP_IMAGE_GEN,
        )
        save_step_result(
            ctx.db,
            ctx.task,
            STEP_IMAGE_GEN,
            result=json.dumps({"images": [], "error": "OPENROUTER_API_KEY missing"}),
            status="failed",
        )
        return
    if not settings.IMGBB_API_KEY:
        add_log(
            ctx.db,
            ctx.task,
            "❌ IMGBB_API_KEY не задан — загрузка изображений невозможна. Заполни в Settings.",
            level="error",
            step=STEP_IMAGE_GEN,
        )
        save_step_result(
            ctx.db,
            ctx.task,
            STEP_IMAGE_GEN,
            result=json.dumps({"images": [], "error": "IMGBB_API_KEY missing"}),
            status="failed",
        )
        return

    prompt_data_raw = ctx.task.step_results.get(STEP_IMAGE_PROMPT_GEN, {}).get("result", "")
    prompt_data = clean_and_parse_json(prompt_data_raw) if prompt_data_raw else {}
    images_to_gen = prompt_data.get("images", []) if isinstance(prompt_data, dict) else []

    if not images_to_gen or (isinstance(prompt_data, dict) and prompt_data.get("skipped")):
        add_log(ctx.db, ctx.task, "No image prompts to process — skipping", step=STEP_IMAGE_GEN)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_GEN, result=json.dumps({"images": []}), status="completed")
        return

    model_id = resolve_image_generation_model(ctx.db)
    fallback_model = settings.IMAGE_MODEL_DEFAULT if model_id != settings.IMAGE_MODEL_DEFAULT else None
    add_log(
        ctx.db,
        ctx.task,
        f"Starting OpenRouter image generation for {len(images_to_gen)} image(s), model={model_id}...",
        step=STEP_IMAGE_GEN,
    )
    mark_step_running(ctx.db, ctx.task, STEP_IMAGE_GEN)

    uploader = ImgBBUploader(api_key=settings.IMGBB_API_KEY)
    keyword_slug = ctx.task.main_keyword.lower().replace(" ", "-")[:30]
    site_slug = ctx.site_name.lower().replace(" ", "-")[:20]

    def _prompt_text(img: dict) -> str:
        return (img.get("image_prompt") or img.get("midjourney_prompt") or "").strip()

    def _run_one(img: dict) -> tuple[dict, ImageResult]:
        gen = OpenRouterImageGenerator(
            api_key=settings.OPENROUTER_API_KEY,
            model=model_id,
            fallback_model=fallback_model,
        )
        text = _prompt_text(img)
        if not text:
            return img, ImageResult(status="failed", error="Empty image prompt")
        return img, gen.generate_and_wait(text, aspect_ratio=img.get("aspect_ratio", "16:9"))

    images_result: list = []
    max_workers = min(4, max(1, len(images_to_gen)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_one, img): img for img in images_to_gen}
        for fut in as_completed(futures):
            img = futures[fut]
            try:
                img, result = fut.result()
            except Exception as e:
                pt = _prompt_text(img)
                images_result.append(
                    {
                        "id": img.get("id"),
                        "section": img.get("section", ""),
                        "image_prompt": pt,
                        "midjourney_prompt": pt,
                        "alt_text": img.get("alt_text", ""),
                        "provider_task_id": "",
                        "status": "failed",
                        "original_url": None,
                        "hosted_url": None,
                        "approved": None,
                        "error": str(e),
                    }
                )
                add_log(ctx.db, ctx.task, f"❌ {img.get('id')}: {e}", level="warn", step=STEP_IMAGE_GEN)
                continue

            pt = _prompt_text(img)
            row = {
                "id": img.get("id"),
                "section": img.get("section", ""),
                "image_prompt": pt,
                "midjourney_prompt": pt,
                "alt_text": img.get("alt_text", ""),
                "provider_task_id": "openrouter-sync",
                "original_url": None,
                "hosted_url": None,
                "approved": None,
                "error": None,
            }
            if result.status == "completed" and result.image_url:
                try:
                    filename = f"{site_slug}_{keyword_slug}_{img.get('id', 'img')}"
                    hosted = uploader.upload_from_data_url(result.image_url, filename)
                    row["status"] = "completed"
                    row["hosted_url"] = hosted.get("url", "")
                    add_log(
                        ctx.db,
                        ctx.task,
                        f"✅ {img.get('id')} → {row['hosted_url'][:60] if row['hosted_url'] else 'ok'}",
                        step=STEP_IMAGE_GEN,
                    )
                except Exception as e:
                    row["status"] = "failed"
                    row["error"] = str(e)
                    add_log(ctx.db, ctx.task, f"❌ {img.get('id')} ImgBB: {e}", level="warn", step=STEP_IMAGE_GEN)
            else:
                row["status"] = "failed"
                row["error"] = result.error or "Image generation failed"
                add_log(
                    ctx.db,
                    ctx.task,
                    f"❌ {img.get('id')}: {row['error']}",
                    level="warn",
                    step=STEP_IMAGE_GEN,
                )
            images_result.append(row)

    completed_count = sum(1 for im in images_result if im["status"] == "completed")
    failed_count = sum(1 for im in images_result if im["status"] == "failed")

    result_payload = {
        "images": images_result,
        "summary": {"total": len(images_result), "completed": completed_count, "failed": failed_count},
        "model": model_id,
    }
    save_step_result(ctx.db, ctx.task, STEP_IMAGE_GEN, result=json.dumps(result_payload, ensure_ascii=False), status="completed")

    if completed_count > 0 or failed_count > 0:
        step_results = dict(ctx.task.step_results or {})
        step_results["_pipeline_pause"] = {"active": True, "reason": "image_review", "message": "Waiting for image review"}
        ctx.task.step_results = step_results
        ctx.task.status = "processing"
        ctx.db.commit()
        add_log(ctx.db, ctx.task, f"🖼️ Image generation done: {completed_count} ok, {failed_count} failed. Waiting for review.", step=STEP_IMAGE_GEN)
    else:
        add_log(ctx.db, ctx.task, "No images generated — continuing pipeline", step=STEP_IMAGE_GEN)


def phase_image_inject(ctx: PipelineContext):
    """Service step: injects approved images into final HTML after html_structure."""
    html_result = ctx.task.step_results.get(STEP_HTML_STRUCT, {}).get("result", "")
    if not html_result:
        add_log(ctx.db, ctx.task, "No HTML structure found — skipping image inject", step=STEP_IMAGE_INJECT)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_INJECT, result="", status="completed", input_word_count=0, output_word_count=0)
        return

    image_data_raw = ctx.task.step_results.get(STEP_IMAGE_GEN, {}).get("result", "")
    if not image_data_raw:
        add_log(ctx.db, ctx.task, "No image data — passing HTML through unchanged", step=STEP_IMAGE_INJECT)
        wc = count_content_words(html_result)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_INJECT, result=html_result, status="completed", input_word_count=wc, output_word_count=wc)
        return

    image_data = clean_and_parse_json(image_data_raw) if isinstance(image_data_raw, str) else image_data_raw
    if not isinstance(image_data, dict):
        wc = count_content_words(html_result)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_INJECT, result=html_result, status="completed", input_word_count=wc, output_word_count=wc)
        return

    approved_images = [img for img in image_data.get("images", []) if img.get("approved") is True and img.get("hosted_url")]

    if not approved_images:
        add_log(ctx.db, ctx.task, "No approved images — cleaning MEDIA comment markers", step=STEP_IMAGE_INJECT)
        cleaned = re.sub(r'<!--\s*MEDIA:.*?-->', '', html_result, flags=re.IGNORECASE | re.DOTALL)
        in_w = count_content_words(html_result)
        out_w = count_content_words(cleaned)
        save_step_result(ctx.db, ctx.task, STEP_IMAGE_INJECT, result=cleaned, status="completed", input_word_count=in_w, output_word_count=out_w)
        return

    add_log(ctx.db, ctx.task, f"Injecting {len(approved_images)} approved images into HTML...", step=STEP_IMAGE_INJECT)
    mark_step_running(ctx.db, ctx.task, STEP_IMAGE_INJECT)

    soup = BeautifulSoup(html_result, "html.parser")
    media_comments = [
        node
        for node in soup.find_all(
            string=lambda text: isinstance(text, Comment) and "MEDIA:" in str(text)
        )
    ]
    injected_count = 0

    for i, img in enumerate(approved_images):
        hosted_url = img["hosted_url"]
        alt_text = img.get("alt_text", "")
        figure_html = (
            f'<figure class="article-image">'
            f'<img src="{hosted_url}" alt="{alt_text}" width="800" loading="lazy">'
            f'<figcaption>{alt_text}</figcaption>'
            f"</figure>"
        )
        figure_fragment = BeautifulSoup(figure_html, "html.parser")
        figure_node = figure_fragment.find("figure")
        if not figure_node:
            continue

        if i < len(media_comments):
            media_comments[i].replace_with(figure_node)
            injected_count += 1
        else:
            all_h2 = soup.find_all("h2")
            if all_h2:
                all_h2[-1].insert_before(figure_node)
                injected_count += 1

    result_html = str(soup)
    result_html = re.sub(r'<!--\s*MEDIA:.*?-->', "", result_html, flags=re.IGNORECASE | re.DOTALL)

    add_log(ctx.db, ctx.task, f"Image injection completed: {injected_count}/{len(approved_images)} inserted", step=STEP_IMAGE_INJECT)
    in_w = count_content_words(html_result)
    out_w = count_content_words(result_html)
    save_step_result(ctx.db, ctx.task, STEP_IMAGE_INJECT, result=result_html, status="completed", input_word_count=in_w, output_word_count=out_w)


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
    mark_step_running(ctx.db, ctx.task, STEP_PRIMARY_GEN)
    draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = call_agent_with_exclude_validation(ctx, "primary_generation", gen_context, step_constant=STEP_PRIMARY_GEN)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Primary Generation completed ({len(draft_html)} chars)", step=STEP_PRIMARY_GEN)
    out_wc = count_content_words(draft_html)
    save_step_result(ctx.db, ctx.task, STEP_PRIMARY_GEN, result=draft_html, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts, exclude_words_violations=violations, output_word_count=out_wc)


def phase_primary_gen_about(ctx: PipelineContext):
    setup_template_vars(ctx)
    gen_context = ""
    add_log(ctx.db, ctx.task, "Starting Primary Generation (About Page)...", step=STEP_PRIMARY_GEN_ABOUT)
    mark_step_running(ctx.db, ctx.task, STEP_PRIMARY_GEN_ABOUT)
    draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = (
        call_agent_with_exclude_validation(
            ctx,
            "primary_generation_about",
            gen_context,
            step_constant=STEP_PRIMARY_GEN_ABOUT,
        )
    )
    ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
    add_log(
        ctx.db,
        ctx.task,
        f"Primary Generation (About) completed ({len(draft_html)} chars)",
        step=STEP_PRIMARY_GEN_ABOUT,
    )
    out_wc = count_content_words(draft_html)
    save_step_result(
        ctx.db,
        ctx.task,
        STEP_PRIMARY_GEN_ABOUT,
        result=draft_html,
        model=actual_model,
        status="completed",
        cost=step_cost,
        variables_snapshot=variables_snapshot,
        resolved_prompts=resolved_prompts,
        exclude_words_violations=violations,
        output_word_count=out_wc,
    )


def phase_primary_gen_legal(ctx: PipelineContext):
    setup_template_vars(ctx)
    inject_legal_template_vars(ctx)
    gen_context = ""
    add_log(ctx.db, ctx.task, "Starting Primary Generation (Legal Page)...", step=STEP_PRIMARY_GEN_LEGAL)
    mark_step_running(ctx.db, ctx.task, STEP_PRIMARY_GEN_LEGAL)
    draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = (
        call_agent_with_exclude_validation(
            ctx,
            "primary_generation_legal",
            gen_context,
            step_constant=STEP_PRIMARY_GEN_LEGAL,
        )
    )
    ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost
    add_log(
        ctx.db,
        ctx.task,
        f"Primary Generation (Legal) completed ({len(draft_html)} chars)",
        step=STEP_PRIMARY_GEN_LEGAL,
    )
    out_wc = count_content_words(draft_html)
    save_step_result(
        ctx.db,
        ctx.task,
        STEP_PRIMARY_GEN_LEGAL,
        result=draft_html,
        model=actual_model,
        status="completed",
        cost=step_cost,
        variables_snapshot=variables_snapshot,
        resolved_prompts=resolved_prompts,
        exclude_words_violations=violations,
        output_word_count=out_wc,
    )


def phase_competitor_comparison(ctx: PipelineContext):
    setup_template_vars(ctx)
    draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
    comparison_context = (
        f"Our article:\n{draft_html}\n\n"
        f"Competitors:\n{ctx.task.competitors_text[:15000]}"
    )
    add_log(ctx.db, ctx.task, "Starting Competitor Comparison...", step=STEP_COMP_COMPARISON)
    mark_step_running(ctx.db, ctx.task, STEP_COMP_COMPARISON)
    comparison_review, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(ctx, "competitor_comparison", comparison_context, variables=ctx.template_vars)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Competitor Comparison completed", step=STEP_COMP_COMPARISON)
    save_step_result(ctx.db, ctx.task, STEP_COMP_COMPARISON, result=comparison_review, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)

def phase_reader_opinion(ctx: PipelineContext):
    setup_template_vars(ctx)
    draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
    reader_context = f"Article:\n{draft_html}"
    add_log(ctx.db, ctx.task, "Starting Reader Opinion analysis...", step=STEP_READER_OPINION)
    mark_step_running(ctx.db, ctx.task, STEP_READER_OPINION)
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
    mark_step_running(ctx.db, ctx.task, STEP_INTERLINK)
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
    mark_step_running(ctx.db, ctx.task, STEP_IMPROVER)
    improved_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = call_agent_with_exclude_validation(ctx, "improver", improver_context, step_constant=STEP_IMPROVER)
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, f"Improver completed ({len(improved_html)} chars)", step=STEP_IMPROVER)
    in_wc = count_content_words(draft_html)
    out_wc = count_content_words(improved_html)
    save_step_result(ctx.db, ctx.task, STEP_IMPROVER, result=improved_html, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts, exclude_words_violations=violations, input_word_count=in_wc, output_word_count=out_wc)

def phase_final_editing(ctx: PipelineContext):
    setup_template_vars(ctx)
    if ctx.use_serp:
        improved_html = ctx.task.step_results.get(STEP_IMPROVER, {}).get("result", "") or ""
        if not improved_html.strip():
            improved_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "") or ""
    else:
        improved_html = (
            ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
            or ctx.task.step_results.get(STEP_PRIMARY_GEN_ABOUT, {}).get("result", "")
            or ctx.task.step_results.get(STEP_PRIMARY_GEN_LEGAL, {}).get("result", "")
            or ""
        )

    # Prompts use {{result_improver}}; without SERP there is no improver step — alias current HTML.
    ctx.template_vars["result_improver"] = improved_html or ""

    avg_words = ctx.template_vars.get("avg_word_count", "0")
    input_word_count = count_content_words(improved_html)
    input_char_count = len(improved_html)

    editing_context = ""
    add_log(ctx.db, ctx.task, "Starting Final Editing...", step=STEP_FINAL_EDIT)
    mark_step_running(ctx.db, ctx.task, STEP_FINAL_EDIT)
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
    output_word_count = count_content_words(final_html)
    output_char_count = len(final_html)

    add_log(ctx.db, ctx.task, 
        f"Final Editing completed | input: {input_word_count} words / {input_char_count} chars | "
        f"output: {output_word_count} words / {output_char_count} chars | "
        f"target avg: {avg_words} words", 
        step=STEP_FINAL_EDIT)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_EDIT, result=final_html, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts, exclude_words_violations=violations, input_word_count=input_word_count, output_word_count=output_word_count)

def phase_html_structure(ctx: PipelineContext):
    setup_template_vars(ctx)
    final_html = _completed_step_body(ctx.task, STEP_FINAL_EDIT)
    if not final_html:
        for key in (STEP_IMPROVER, STEP_PRIMARY_GEN, STEP_PRIMARY_GEN_ABOUT, STEP_PRIMARY_GEN_LEGAL):
            final_html = _completed_step_body(ctx.task, key)
            if final_html:
                break

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
    mark_step_running(ctx.db, ctx.task, STEP_HTML_STRUCT)
    structured_html, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, "html_structure", html_struct_context, variables=ctx.template_vars
    )
    ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + step_cost

    input_wc = count_content_words(final_html)
    output_wc = count_content_words(structured_html)
    loss_pct = ((input_wc - output_wc) / input_wc * 100.0) if input_wc > 0 else 0.0

    max_rec = getattr(settings, "SELF_CHECK_MAX_RETRIES", 1)
    retry_budget = float(getattr(settings, "SELF_CHECK_MAX_COST_PER_STEP", 0.10) or 0.0)

    if input_wc > 0 and loss_pct > 7 and max_rec >= 1 and retry_budget > 0:
        add_log(
            ctx.db,
            ctx.task,
            f"Content loss {loss_pct:.1f}% detected, attempting recovery (single retry)...",
            level="warn",
            step=STEP_HTML_STRUCT,
        )
        prev_loss = loss_pct
        recovery_context = (
            f"PREVIOUS ATTEMPT FAILED: You lost {prev_loss:.1f}% of content words.\n"
            f"Input had {input_wc} words but your output only had {output_wc} words.\n\n"
            f"YOU MUST OUTPUT ALL {input_wc} WORDS from the article below.\n"
            f"Do NOT summarize or shorten. Insert the COMPLETE article into the template.\n\n"
            f"{html_struct_context}"
        )
        retry_html, retry_cost, retry_model, retry_prompts, retry_vars = call_agent(
            ctx, "html_structure", recovery_context, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, "total_cost", 0.0) + retry_cost
        if retry_cost > retry_budget:
            add_log(
                ctx.db,
                ctx.task,
                f"Recovery retry cost ${retry_cost:.4f} exceeded per-step retry budget ${retry_budget:.4f}.",
                level="warn",
                step=STEP_HTML_STRUCT,
            )
        retry_wc = count_content_words(retry_html)
        retry_loss = ((input_wc - retry_wc) / input_wc * 100.0) if input_wc > 0 else 0.0
        if retry_loss < prev_loss:
            structured_html = retry_html
            output_wc = retry_wc
            loss_pct = retry_loss
            step_cost += retry_cost
            actual_model = retry_model
            resolved_prompts = retry_prompts
            variables_snapshot = retry_vars
            add_log(
                ctx.db,
                ctx.task,
                f"Recovery improved: {retry_loss:.1f}% loss (was {prev_loss:.1f}%)",
                step=STEP_HTML_STRUCT,
            )

    if input_wc > 0 and loss_pct > 20:
        add_log(
            ctx.db,
            ctx.task,
            f"Content loss still {loss_pct:.1f}% after recovery. Using programmatic insert.",
            level="warn",
            step=STEP_HTML_STRUCT,
        )
        template_raw = ctx.template_vars.get("site_template_html", "") or ""
        structured_html = programmatic_html_insert(template_raw, final_html)
        output_wc = count_content_words(structured_html)
        loss_pct = ((input_wc - output_wc) / input_wc * 100.0) if input_wc > 0 else 0.0
        add_log(
            ctx.db,
            ctx.task,
            f"Programmatic HTML insert: {output_wc} words, loss now {loss_pct:.1f}%",
            level="info",
            step=STEP_HTML_STRUCT,
        )

    wc_kw = {}
    if input_wc > 0 and loss_pct > 7:
        add_log(
            ctx.db,
            ctx.task,
            f"⚠️ WORD COUNT DROP: html_structure lost {loss_pct:.1f}% of content words! "
            f"Input: {input_wc} words → Output: {output_wc} words. "
            f"Maximum allowed loss: 7%",
            level="warn",
            step=STEP_HTML_STRUCT,
        )
        wc_kw["word_count_warning"] = True
        wc_kw["word_loss_percentage"] = round(loss_pct, 1)

    add_log(ctx.db, ctx.task, f"HTML Structure completed ({len(structured_html)} chars)", step=STEP_HTML_STRUCT)
    save_step_result(
        ctx.db,
        ctx.task,
        STEP_HTML_STRUCT,
        result=structured_html,
        model=actual_model,
        status="completed",
        cost=step_cost,
        variables_snapshot=variables_snapshot,
        resolved_prompts=resolved_prompts,
        input_word_count=input_wc,
        output_word_count=output_wc,
        **wc_kw,
    )

def phase_content_fact_check(ctx: PipelineContext):
    if not settings.FACT_CHECK_ENABLED:
        save_step_result(
            ctx.db,
            ctx.task,
            STEP_CONTENT_FACT_CHECK,
            result='{"verification_status": "skipped", "issues": [], "summary": "Fact-check disabled in settings."}',
            status="completed",
        )
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
    mark_step_running(ctx.db, ctx.task, STEP_CONTENT_FACT_CHECK)
    
    try:
        fact_check_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
            ctx, "content_fact_checking", fact_check_context,
            response_format={"type": "json_object"}, variables=ctx.template_vars
        )
        ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
        
        add_log(ctx.db, ctx.task, f"Fact-Checking completed", step=STEP_CONTENT_FACT_CHECK)
        save_step_result(ctx.db, ctx.task, STEP_CONTENT_FACT_CHECK, result=fact_check_json_str, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)
    except Exception as e:
        add_log(ctx.db, ctx.task, f"Fact-checking agent failed or not found: {str(e)}", level="warn", step=STEP_CONTENT_FACT_CHECK)
        save_step_result(ctx.db, ctx.task, STEP_CONTENT_FACT_CHECK, result='{"verification_status": "warn", "issues": [], "summary": "Failed to run content_fact_checking agent."}', status="completed")

def phase_meta_generation(ctx: PipelineContext):
    setup_template_vars(ctx)
    structured_html = pick_html_for_meta(ctx)
    meta_context = f"Article HTML:\n{structured_html}"
    add_log(ctx.db, ctx.task, "Generating Meta Tags (JSON)...", step=STEP_META_GEN)
    mark_step_running(ctx.db, ctx.task, STEP_META_GEN)
    meta_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, "meta_generation", meta_context,
        response_format={"type": "json_object"}, variables=ctx.template_vars
    )
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    raw_preview = (meta_json_str or "")[:500]
    add_log(
        ctx.db,
        ctx.task,
        f"meta_generation raw (first 500): {raw_preview}",
        level="debug",
        step=STEP_META_GEN,
    )
    add_log(ctx.db, ctx.task, f"Meta Tags Generation completed", step=STEP_META_GEN)
    save_step_result(ctx.db, ctx.task, STEP_META_GEN, result=meta_json_str, model=actual_model, status="completed", cost=step_cost, variables_snapshot=variables_snapshot, resolved_prompts=resolved_prompts)


PHASE_REGISTRY = {
    STEP_SERP: phase_serp,
    STEP_SCRAPING: phase_scraping,
    STEP_AI_ANALYSIS: phase_ai_structure,
    STEP_CHUNK_ANALYSIS: phase_chunk_analysis,
    STEP_COMP_STRUCTURE: phase_competitor_structure,
    STEP_FINAL_ANALYSIS: phase_final_structure,
    STEP_STRUCTURE_FACT_CHECK: phase_structure_fact_check,
    STEP_IMAGE_PROMPT_GEN: phase_image_prompt_gen,
    STEP_IMAGE_GEN: phase_image_gen,
    STEP_PRIMARY_GEN: phase_primary_gen,
    STEP_PRIMARY_GEN_ABOUT: phase_primary_gen_about,
    STEP_PRIMARY_GEN_LEGAL: phase_primary_gen_legal,
    STEP_COMP_COMPARISON: phase_competitor_comparison,
    STEP_READER_OPINION: phase_reader_opinion,
    STEP_INTERLINK: phase_interlink,
    STEP_IMPROVER: phase_improver,
    STEP_FINAL_EDIT: phase_final_editing,
    STEP_HTML_STRUCT: phase_html_structure,
    STEP_IMAGE_INJECT: phase_image_inject,
    STEP_META_GEN: phase_meta_generation,
    STEP_CONTENT_FACT_CHECK: phase_content_fact_check,
}


def _auto_approve_images(ctx: PipelineContext) -> None:
    """
    Approve all successfully generated images (status completed + hosted_url), clear image review pause.
    Mirrors POST /tasks/{id}/approve-images for site-project auto_mode runs.
    """
    import json as _json

    step_results = dict(ctx.task.step_results or {})
    image_gen_result = step_results.get(STEP_IMAGE_GEN, {}).get("result", "")
    if not image_gen_result:
        step_results["_pipeline_pause"] = {"active": False, "reason": "image_review"}
        step_results["_images_approved"] = True
        ctx.task.step_results = step_results
        ctx.db.commit()
        add_log(ctx.db, ctx.task, "auto_mode: no image_generation payload — cleared image pause", step=STEP_IMAGE_GEN)
        return
    try:
        data = _json.loads(image_gen_result) if isinstance(image_gen_result, str) else image_gen_result
    except Exception:
        step_results["_pipeline_pause"] = {"active": False, "reason": "image_review"}
        step_results["_images_approved"] = True
        ctx.task.step_results = step_results
        ctx.db.commit()
        add_log(ctx.db, ctx.task, "auto_mode: could not parse image_generation JSON — cleared image pause", level="warn", step=STEP_IMAGE_GEN)
        return
    images = data.get("images", [])
    approved_n = 0
    for img in images:
        if img.get("status") == "completed" and img.get("hosted_url"):
            img["approved"] = True
            approved_n += 1
        else:
            img["approved"] = False
    step_data = dict(step_results.get(STEP_IMAGE_GEN, {}))
    step_data["result"] = _json.dumps(data, ensure_ascii=False)
    step_results[STEP_IMAGE_GEN] = step_data
    step_results["_pipeline_pause"] = {"active": False, "reason": "image_review"}
    step_results["_images_approved"] = True
    ctx.task.step_results = step_results
    ctx.db.commit()
    add_log(
        ctx.db,
        ctx.task,
        f"auto_mode: approved {approved_n} image(s) with completed status, continuing pipeline",
        step=STEP_IMAGE_GEN,
    )


def run_pipeline(db: Session, task_id: str, auto_mode: bool = False):
    ctx = PipelineContext(db, task_id, auto_mode=auto_mode)

    ctx.task.status = "processing"
    
    if ctx.task.total_cost is None:
        ctx.task.total_cost = 0.0
        
    db.commit()
    
    add_log(db, ctx.task, "🚀 Pipeline started / resumed", step=None)

    try:
        # --- Check for active pause (on pipeline resume) ---
        step_results = ctx.task.step_results or {}
        pause_state = step_results.get("_pipeline_pause", {})
        if isinstance(pause_state, dict) and pause_state.get("active"):
            reason = pause_state.get("reason", "unknown")
            if reason == "image_review" and not step_results.get("_images_approved"):
                if not auto_mode:
                    add_log(db, ctx.task, "⏸️ Pipeline paused: waiting for image review", step=None)
                    return
                _auto_approve_images(ctx)
            elif reason == "serp_review" and not step_results.get("_serp_urls_approved"):
                if not auto_mode:
                    add_log(db, ctx.task, "⏸️ Pipeline paused: waiting for SERP URLs review", step=None)
                    ctx.task.status = "paused"
                    db.commit()
                    return
                updated = dict(step_results)
                updated["_serp_urls_approved"] = True
                updated["_pipeline_pause"] = {"active": False, "reason": "serp_review"}
                ctx.task.step_results = updated
                db.commit()
                add_log(db, ctx.task, "auto_mode: skipped SERP URL review pause", step=None)
            elif reason == "test_mode" and not step_results.get("test_mode_approved"):
                if not auto_mode:
                    add_log(db, ctx.task, "⏸️ Pipeline paused: waiting for test mode approval", step=None)
                    return
                updated = dict(ctx.task.step_results or {})
                updated["test_mode_approved"] = True
                updated["waiting_for_approval"] = False
                updated["_pipeline_pause"] = {"active": False, "reason": "test_mode"}
                ctx.task.step_results = updated
                db.commit()
                add_log(db, ctx.task, "auto_mode: test mode approval applied, continuing", step=None)
            else:
                # Pause was resolved — clear it
                updated = dict(step_results)
                updated["_pipeline_pause"] = {"active": False, "reason": reason}
                ctx.task.step_results = updated
                db.commit()

        if ctx.pipeline_steps is not None:
            steps = list(ctx.pipeline_steps)
        else:
            steps = (
                list(PIPELINE_PRESETS["full"])
                if ctx.use_serp
                else [
                    STEP_PRIMARY_GEN,
                    STEP_FINAL_EDIT,
                    STEP_HTML_STRUCT,
                    STEP_META_GEN,
                ]
            )

        preset_name = (
            (getattr(ctx.blueprint_page, "pipeline_preset", None) or "full")
            if ctx.blueprint_page
            else "standalone"
        )

        if not pipeline_steps_use_serp(steps):
            if not ctx.task.outline:
                ctx.task.serp_data = ctx.task.serp_data or {}
                ctx.task.competitors_text = ctx.task.competitors_text or ""
                ctx.task.outline = {
                    "final_outline": {"page_title": ctx.page_title, "sections": []},
                }
                ctx.outline_data = ctx.task.outline
                db.commit()

        merged_plan = dict(ctx.task.step_results or {})
        merged_plan["_pipeline_plan"] = {"steps": steps}
        ctx.task.step_results = merged_plan
        db.commit()

        add_log(
            db,
            ctx.task,
            f"Pipeline preset: {preset_name}, steps: {len(steps)}",
            step=None,
        )

        for step_name in steps:
            phase_func = PHASE_REGISTRY.get(step_name)
            if not phase_func:
                add_log(
                    db,
                    ctx.task,
                    f"⚠️ Unknown step '{step_name}' — skipped",
                    level="warn",
                    step=step_name,
                )
                continue

            run_phase(db, ctx.task, step_name, phase_func, ctx)

            if step_name == STEP_SERP:
                sr = dict(ctx.task.step_results or {})
                pause_st = sr.get("_pipeline_pause", {})
                if (
                    isinstance(pause_st, dict)
                    and pause_st.get("active")
                    and pause_st.get("reason") == "serp_review"
                    and not sr.get("_serp_urls_approved")
                    and not auto_mode
                ):
                    return

            if step_name.startswith("primary_generation") and settings.TEST_MODE:
                step_results_tm = ctx.task.step_results or {}
                if not step_results_tm.get("test_mode_approved"):
                    if auto_mode:
                        updated = dict(step_results_tm)
                        updated["test_mode_approved"] = True
                        updated["waiting_for_approval"] = False
                        updated["_pipeline_pause"] = {"active": False, "reason": "test_mode"}
                        ctx.task.step_results = updated
                        db.commit()
                        add_log(db, ctx.task, "auto_mode: skipped TEST MODE pause after primary generation", step=None)
                    else:
                        updated = dict(step_results_tm)
                        updated["waiting_for_approval"] = True
                        updated["_pipeline_pause"] = {
                            "active": True,
                            "reason": "test_mode",
                            "message": "Test mode: review primary generation",
                        }
                        ctx.task.step_results = updated
                        ctx.task.status = "processing"
                        db.commit()
                        add_log(
                            db,
                            ctx.task,
                            "🛑 TEST MODE: Pausing after primary generation",
                            step=None,
                        )
                        return

            if step_name == STEP_IMAGE_GEN:
                step_results_ig = dict(ctx.task.step_results or {})
                pause_st = step_results_ig.get("_pipeline_pause", {})
                if (
                    isinstance(pause_st, dict)
                    and pause_st.get("active")
                    and pause_st.get("reason") == "image_review"
                ):
                    if not step_results_ig.get("_images_approved"):
                        if auto_mode:
                            _auto_approve_images(ctx)
                        else:
                            return

        # Assemble and SAVE
        try:
            add_log(db, ctx.task, "Starting article assembly and saving...", step=None)
            structured_html = pick_structured_html_for_assembly(ctx)
            if not structured_html.strip():
                raise ValueError(
                    "No HTML body produced by pipeline steps — cannot assemble article."
                )
            meta_json_str = ctx.task.step_results.get(STEP_META_GEN, {}).get("result", "{}")
            if not isinstance(meta_json_str, str):
                meta_json_str = json.dumps(meta_json_str, ensure_ascii=False) if meta_json_str else "{}"
            meta_data = clean_and_parse_json(meta_json_str)

            add_log(
                db,
                ctx.task,
                f"meta_data keys: {list(meta_data.keys()) if meta_data else 'EMPTY'}",
                level="debug",
                step=STEP_META_GEN,
            )

            meta_extracted = extract_meta_from_parsed(meta_data)
            title = meta_extracted["title"]
            description = meta_extracted["description"]
            h1_meta = meta_extracted.get("h1", "")

            add_log(
                db,
                ctx.task,
                f"meta extracted: title='{title[:80]}', desc='{description[:80]}', h1='{h1_meta[:80]}'",
                level="debug",
                step=STEP_META_GEN,
            )

            if not title:
                title = ctx.task.main_keyword.title()
                add_log(
                    db,
                    ctx.task,
                    "⚠️ meta_generation не вернул Title — fallback на keyword",
                    level="warn",
                    step=STEP_META_GEN,
                )

            word_count = count_content_words(structured_html)
            full_page = generate_full_page(
                db,
                str(ctx.task.target_site_id),
                structured_html,
                title,
                description,
                project_id=str(ctx.task.project_id) if ctx.task.project_id else None,
            )

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

            existing = db.query(GeneratedArticle).filter(GeneratedArticle.task_id == ctx.task.id).first()
            if not existing:
                article = GeneratedArticle(
                    task_id=ctx.task.id,
                    title=title,
                    description=description,
                    meta_data=meta_data,
                    html_content=structured_html,
                    full_page_html=full_page,
                    word_count=word_count,
                    fact_check_status=fact_check_status_val,
                    fact_check_issues=fact_check_issues_val,
                    needs_review=needs_review_val,
                )
                db.add(article)
            else:
                existing.title = title
                existing.description = description
                existing.meta_data = meta_data
                existing.html_content = structured_html
                existing.full_page_html = full_page
                existing.word_count = word_count
                existing.fact_check_status = fact_check_status_val
                existing.fact_check_issues = fact_check_issues_val
                existing.needs_review = needs_review_val
                article = existing

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
