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
from app.services.template_engine import generate_full_page
from app.services.notifier import notify_task_success, notify_task_failed
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

def save_step_result(db: Session, task: Task, step_name: str, result: str, model: str = None, status: str = "completed"):
    if task.step_results is None:
        task.step_results = {}
    
    step_data = {
        "status": status,
        "result": result[:50000] if result else None,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    if model:
        step_data["model"] = model
    
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

def apply_template_vars(text: str, variables: dict) -> str:
    """Replace {{variable_name}} placeholders in text with actual values."""
    if not text:
        return text
    def replacer(match):
        key = match.group(1).strip()
        return str(variables.get(key, match.group(0)))  # keep original if not found
    return re.sub(r'\{\{(.+?)\}\}', replacer, text)

def call_agent(db: Session, agent_name: str, context: str, response_format=None, variables: dict = None):
    """Helper: load prompt config for agent_name, apply template vars, merge context, call LLM."""
    prompt = get_prompt_obj(db, agent_name)
    
    if getattr(prompt, "skip_in_pipeline", False):
        print(f"Agent {agent_name} skipped (toggle off)")
        return ""
    
    system_text = prompt.system_prompt
    user_template = prompt.user_prompt or ""
    
    if variables:
        system_text = apply_template_vars(system_text, variables)
        user_template = apply_template_vars(user_template, variables)
    
    user_msg = f"{user_template}\n\n[CONTEXT]\n{context}" if user_template else context
    
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
    
    return generate_text(**kwargs)

def setup_vars(ctx: PipelineContext):
    scrape_info = ctx.outline_data.get("scrape_info", {})
    avg_words = scrape_info.get("avg_words", 800)
    headers_info = scrape_info.get("headers", [])
    
    paa = ctx.task.serp_data.get("paa", []) if ctx.task.serp_data else []
    related = ctx.task.serp_data.get("related_searches", []) if ctx.task.serp_data else []
    add_kw_text = f"\nAdditional Keywords: {ctx.task.additional_keywords}" if ctx.task.additional_keywords else ""

    ctx.base_context = (
        f"Keyword: {ctx.task.main_keyword}{add_kw_text}\n"
        f"Country: {ctx.task.country}\n"
        f"Language: {ctx.task.language}\n"
        f"People Also Ask: {json.dumps(paa, ensure_ascii=False)}\n"
        f"Related Searches: {json.dumps(related, ensure_ascii=False)}\n"
        f"Competitors Headers: {json.dumps(headers_info, ensure_ascii=False)}\n"
        f"Target word count: {avg_words}"
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
    }

def setup_template_vars(ctx: PipelineContext):
    author_style, imitation, year, face, target_audience, rhythms_style = "", "", "", "", "", ""
    author_name = ""
    
    if ctx.task.author_id:
        author = ctx.db.query(Author).filter(Author.id == ctx.task.author_id).first()
        if author:
            author_style = author.style_prompt or ""
            imitation = author.imitation or ""
            year = author.year or ""
            face = author.face or ""
            target_audience = author.target_audience or ""
            rhythms_style = author.rhythms_style or ""
            author_name = author.author or ""

    ctx.author_block = (
        f"Author Style/Text Block: {author_style}\n"
        f"Imitation (Mimicry): {imitation}\n"
        f"Year: {year}\n"
        f"Face: {face}\n"
        f"Target Audience: {target_audience}\n"
        f"Rhythms & Style: {rhythms_style}\n"
        f"Exclude Words: {settings.EXCLUDE_WORDS}"
    )
    
    ctx.template_vars = {
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
        "exclude_words": settings.EXCLUDE_WORDS,
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
    }

def run_phase(db: Session, task: Task, step_key: str, phase_func, *args, **kwargs):
    """Wrapper that skips phase_func if already completed."""
    if task.step_results and step_key in task.step_results:
        if task.step_results[step_key].get("status") == "completed":
            print(f"Skipping {step_key} - already completed")
            return
            
    print(f"Running phase: {step_key}")
    phase_func(*args, **kwargs)

def phase_serp(ctx: PipelineContext):
    if not ctx.task.serp_data:
        add_log(ctx.db, ctx.task, "Fetching SERP data...", step=STEP_SERP)
        save_step_result(ctx.db, ctx.task, STEP_SERP, result=None, status="running")
        serp_data = fetch_serp_data(ctx.task.main_keyword, ctx.task.country, ctx.task.language)
        ctx.task.serp_data = serp_data
        ctx.db.commit()
        add_log(ctx.db, ctx.task, f"SERP Research completed.", step=STEP_SERP)
        save_step_result(ctx.db, ctx.task, STEP_SERP, result=json.dumps(serp_data.get("urls", []), ensure_ascii=False), status="completed")

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
        add_log(ctx.db, ctx.task, f"Scraped competitors. Avg word count: {scrape_data['average_word_count']}", step=STEP_SCRAPING)
        save_step_result(ctx.db, ctx.task, STEP_SCRAPING, result=f"Scraped URLs. Avg words: {scrape_data['average_word_count']}", status="completed")

def phase_ai_structure(ctx: PipelineContext):
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting AI Structure Analysis...", step=STEP_AI_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_AI_ANALYSIS, result=None, status="running")
    ai_structure = call_agent(
        ctx.db, "ai_structure_analysis", ctx.base_context, 
        response_format={"type": "json_object"}, variables=ctx.analysis_vars
    )
    
    ctx.analysis_vars["result_ai_structure_analysis"] = ai_structure
    ctx.outline_data["ai_structure"] = ai_structure
    
    ai_struct_data = clean_and_parse_json(ai_structure)
    if ai_struct_data:
        ctx.analysis_vars["intent"] = ai_struct_data.get("intent", "")
        ctx.analysis_vars["Taxonomy"] = ai_struct_data.get("Taxonomy", "")
        ctx.analysis_vars["Attention"] = ai_struct_data.get("Attention", "")
        ctx.analysis_vars["structura"] = ai_struct_data.get("structura", "")
        ctx.outline_data["ai_structure_parsed"] = ai_struct_data
    else:
        add_log(ctx.db, ctx.task, f"Warning: Failed to parse ai_structure_analysis JSON", level="warn", step=STEP_AI_ANALYSIS)

    ctx.task.outline = ctx.outline_data
    ctx.db.commit()
    add_log(ctx.db, ctx.task, f"AI Structure Analysis completed ({len(ai_structure)} chars)", step=STEP_AI_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_AI_ANALYSIS, result=ai_structure, status="completed")

def phase_chunk_analysis(ctx: PipelineContext):
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting Chunk Cluster Analysis...", step=STEP_CHUNK_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_CHUNK_ANALYSIS, result=None, status="running")
    ai_structure = ctx.outline_data.get("ai_structure", "")
    chunk_context = f"{ctx.base_context}\n\nAI Structure Analysis:\n{ai_structure}"
    chunk_analysis = call_agent(ctx.db, "chunk_cluster_analysis", chunk_context, variables=ctx.analysis_vars)
    
    ctx.analysis_vars["result_chunk_cluster_analysis"] = chunk_analysis
    ctx.outline_data["chunk_analysis"] = chunk_analysis
    ctx.task.outline = ctx.outline_data
    ctx.db.commit()
    add_log(ctx.db, ctx.task, f"Chunk Cluster Analysis completed ({len(chunk_analysis)} chars)", step=STEP_CHUNK_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_CHUNK_ANALYSIS, result=chunk_analysis, status="completed")

def phase_competitor_structure(ctx: PipelineContext):
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting Competitor Structure Analysis...", step=STEP_COMP_STRUCTURE)
    save_step_result(ctx.db, ctx.task, STEP_COMP_STRUCTURE, result=None, status="running")
    chunk_analysis = ctx.outline_data.get("chunk_analysis", "")
    competitor_context = (
        f"{ctx.base_context}\n\n"
        f"Competitors Text:\n{ctx.task.competitors_text[:20000]}\n\n"
        f"Chunk Analysis:\n{chunk_analysis}"
    )
    competitor_structure = call_agent(ctx.db, "competitor_structure_analysis", competitor_context, variables=ctx.analysis_vars)
    
    ctx.analysis_vars["result_competitor_structure_analysis"] = competitor_structure
    ctx.outline_data["competitor_structure"] = competitor_structure
    ctx.task.outline = ctx.outline_data
    ctx.db.commit()
    add_log(ctx.db, ctx.task, f"Competitor Structure Analysis completed ({len(competitor_structure)} chars)", step=STEP_COMP_STRUCTURE)
    save_step_result(ctx.db, ctx.task, STEP_COMP_STRUCTURE, result=competitor_structure, status="completed")

def phase_final_structure(ctx: PipelineContext):
    setup_vars(ctx)
    add_log(ctx.db, ctx.task, "Starting Final Structure Analysis (JSON)...", step=STEP_FINAL_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_ANALYSIS, result=None, status="running")
    
    final_analysis_context = (
        f"{ctx.base_context}\n\n"
        f"AI Structure Analysis:\n{ctx.outline_data.get('ai_structure', '')}\n\n"
        f"Chunk Analysis:\n{ctx.outline_data.get('chunk_analysis', '')}\n\n"
        f"Competitor Structure Analysis:\n{ctx.outline_data.get('competitor_structure', '')}"
    )
    outline_json_str = call_agent(
        ctx.db, "final_structure_analysis", final_analysis_context,
        response_format={"type": "json_object"}, variables=ctx.analysis_vars
    )
    
    ctx.outline_data["final_outline"] = clean_and_parse_json(outline_json_str)
    ctx.outline_data["final_structure"] = outline_json_str
    ctx.task.outline = ctx.outline_data
    ctx.db.commit()
    add_log(ctx.db, ctx.task, f"Final Structure Analysis completed", step=STEP_FINAL_ANALYSIS)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_ANALYSIS, result=outline_json_str, status="completed")

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
    draft_html = call_agent(ctx.db, "primary_generation", gen_context, variables=ctx.template_vars)
    
    add_log(ctx.db, ctx.task, f"Primary Generation completed ({len(draft_html)} chars)", step=STEP_PRIMARY_GEN)
    save_step_result(ctx.db, ctx.task, STEP_PRIMARY_GEN, result=draft_html, status="completed")

def phase_competitor_comparison(ctx: PipelineContext):
    setup_template_vars(ctx)
    draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
    comparison_context = (
        f"Our article:\n{draft_html}\n\n"
        f"Competitors:\n{ctx.task.competitors_text[:15000]}"
    )
    add_log(ctx.db, ctx.task, "Starting Competitor Comparison...", step=STEP_COMP_COMPARISON)
    save_step_result(ctx.db, ctx.task, STEP_COMP_COMPARISON, result=None, status="running")
    comparison_review = call_agent(ctx.db, "competitor_comparison", comparison_context, variables=ctx.template_vars)
    
    add_log(ctx.db, ctx.task, f"Competitor Comparison completed", step=STEP_COMP_COMPARISON)
    save_step_result(ctx.db, ctx.task, STEP_COMP_COMPARISON, result=comparison_review, status="completed")

def phase_reader_opinion(ctx: PipelineContext):
    setup_template_vars(ctx)
    draft_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
    reader_context = f"Article:\n{draft_html}"
    add_log(ctx.db, ctx.task, "Starting Reader Opinion analysis...", step=STEP_READER_OPINION)
    save_step_result(ctx.db, ctx.task, STEP_READER_OPINION, result=None, status="running")
    reader_feedback = call_agent(ctx.db, "reader_opinion", reader_context, variables=ctx.template_vars)
    
    add_log(ctx.db, ctx.task, f"Reader Opinion completed", step=STEP_READER_OPINION)
    save_step_result(ctx.db, ctx.task, STEP_READER_OPINION, result=reader_feedback, status="completed")

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
    interlink_suggestions = call_agent(ctx.db, "interlinking_citations", interlink_context, variables=ctx.template_vars)
    
    add_log(ctx.db, ctx.task, f"Interlinking & Citations completed", step=STEP_INTERLINK)
    save_step_result(ctx.db, ctx.task, STEP_INTERLINK, result=interlink_suggestions, status="completed")

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
    improved_html = call_agent(ctx.db, "improver", improver_context, variables=ctx.template_vars)
    
    add_log(ctx.db, ctx.task, f"Improver completed ({len(improved_html)} chars)", step=STEP_IMPROVER)
    save_step_result(ctx.db, ctx.task, STEP_IMPROVER, result=improved_html, status="completed")

def phase_final_editing(ctx: PipelineContext):
    setup_template_vars(ctx)
    if ctx.use_serp:
        improved_html = ctx.task.step_results.get(STEP_IMPROVER, {}).get("result", "")
    else:
        improved_html = ctx.task.step_results.get(STEP_PRIMARY_GEN, {}).get("result", "")
        
    outline_json = ctx.task.outline.get("final_outline", {})
    editing_context = (
        f"Improved HTML:\n{improved_html}\n\n"
        f"Original Outline:\n{json.dumps(outline_json, ensure_ascii=False)}\n\n"
        f"Review & verify this HTML article matches the outline structure."
    )
    add_log(ctx.db, ctx.task, "Starting Final Editing...", step=STEP_FINAL_EDIT)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_EDIT, result=None, status="running")
    final_html = call_agent(ctx.db, "final_editing", editing_context, variables=ctx.template_vars)
    
    add_log(ctx.db, ctx.task, f"Final Editing completed ({len(final_html)} chars)", step=STEP_FINAL_EDIT)
    save_step_result(ctx.db, ctx.task, STEP_FINAL_EDIT, result=final_html, status="completed")

def phase_html_structure(ctx: PipelineContext):
    setup_template_vars(ctx)
    final_html = ctx.task.step_results.get(STEP_FINAL_EDIT, {}).get("result", "")
    html_struct_context = (
        f"Article HTML:\n{final_html}\n\n"
        f"Keyword: {ctx.task.main_keyword}\n"
        f"Language: {ctx.task.language}"
    )
    add_log(ctx.db, ctx.task, "Starting HTML Structure formatting...", step=STEP_HTML_STRUCT)
    save_step_result(ctx.db, ctx.task, STEP_HTML_STRUCT, result=None, status="running")
    structured_html = call_agent(ctx.db, "html_structure", html_struct_context, variables=ctx.template_vars)
    
    add_log(ctx.db, ctx.task, f"HTML Structure completed ({len(structured_html)} chars)", step=STEP_HTML_STRUCT)
    save_step_result(ctx.db, ctx.task, STEP_HTML_STRUCT, result=structured_html, status="completed")

def phase_meta_generation(ctx: PipelineContext):
    setup_template_vars(ctx)
    structured_html = ctx.task.step_results.get(STEP_HTML_STRUCT, {}).get("result", "")
    meta_context = f"Article HTML:\n{structured_html}"
    add_log(ctx.db, ctx.task, "Generating Meta Tags (JSON)...", step=STEP_META_GEN)
    save_step_result(ctx.db, ctx.task, STEP_META_GEN, result=None, status="running")
    meta_json_str = call_agent(
        ctx.db, "meta_generation", meta_context,
        response_format={"type": "json_object"}, variables=ctx.template_vars
    )
    add_log(ctx.db, ctx.task, f"Meta Tags Generation completed", step=STEP_META_GEN)
    save_step_result(ctx.db, ctx.task, STEP_META_GEN, result=meta_json_str, status="completed")

def run_pipeline(db: Session, task_id: str):
    ctx = PipelineContext(db, task_id)

    ctx.task.status = "processing"
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
        run_phase(db, ctx.task, STEP_HTML_STRUCT, phase_html_structure, ctx)
        run_phase(db, ctx.task, STEP_META_GEN, phase_meta_generation, ctx)

        # Assemble and SAVE
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

        # Verify if an article exists already for this task
        existing = db.query(GeneratedArticle).filter(GeneratedArticle.task_id == ctx.task.id).first()
        if not existing:
            article = GeneratedArticle(
                task_id=ctx.task.id,
                title=title,
                description=description,
                html_content=structured_html,
                full_page_html=full_page,
                word_count=word_count
            )
            db.add(article)

        ctx.task.status = "completed"
        db.commit()
        
        add_log(db, ctx.task, "✅ Pipeline finished successfully", step=None)
        notify_task_success(str(ctx.task.id), ctx.task.main_keyword, ctx.site_name, word_count)

    except Exception as e:
        ctx.task.status = "failed"
        ctx.task.error_log = traceback.format_exc()
        db.commit()
        add_log(db, ctx.task, f"❌ Pipeline failed: {str(e)}", level="error", step=None)
        notify_task_failed(str(ctx.task.id), ctx.task.main_keyword, str(e), ctx.site_name)
