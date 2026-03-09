import json
import traceback
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.article import GeneratedArticle
from app.models.site import Site
from app.models.author import Author
from app.models.prompt import Prompt
from app.services.serp import fetch_serp_data
from app.services.scraper import scrape_urls
from app.services.llm import generate_text
from app.services.template_engine import generate_full_page
from app.services.notifier import notify_task_success, notify_task_failed
from app.config import settings
from app.models.blueprint import BlueprintPage
from app.models.project import SiteProject

def get_prompt_obj(db: Session, agent_name: str) -> Prompt:
    prompt_obj = db.query(Prompt).filter(Prompt.agent_name == agent_name, Prompt.is_active == True).first()
    if not prompt_obj:
        raise Exception(f"No active prompt found for agent: {agent_name}")
    return prompt_obj

import re
import datetime

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
    db.commit()

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
    
    # Apply template variable substitution
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

def run_pipeline(db: Session, task_id: str):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        print(f"Task {task_id} not found!")
        return

    task.status = "processing"
    db.commit()
    
    add_log(db, task, "🚀 Pipeline started", step=None)

    site = db.query(Site).filter(Site.id == task.target_site_id).first()
    site_name = site.name if site else "Unknown Site"

    blueprint_page = None
    all_site_pages = []
    page_slug = ""
    page_title = ""
    use_serp = True

    if task.blueprint_page_id and task.project_id:
        blueprint_page = db.query(BlueprintPage).filter(BlueprintPage.id == task.blueprint_page_id).first()
        if blueprint_page:
            page_slug = blueprint_page.page_slug
            page_title = blueprint_page.page_title
            use_serp = blueprint_page.use_serp
            
            project = db.query(SiteProject).filter(SiteProject.id == task.project_id).first()
            if project:
                all_pages_db = db.query(BlueprintPage).filter(BlueprintPage.blueprint_id == project.blueprint_id).order_by(BlueprintPage.sort_order).all()
                all_site_pages = [{"slug": p.page_slug, "title": p.page_title, "type": p.page_type, "url": p.filename} for p in all_pages_db]

    try:
        # ================================================================
        # Phase 1: SERP Research
        # ================================================================
        if use_serp:
            if not task.serp_data:
                add_log(db, task, "Fetching SERP data...", step="serp_research")
                save_step_result(db, task, "serp_research", result=None, status="running")
                serp_data = fetch_serp_data(task.main_keyword, task.country, task.language)
                task.serp_data = serp_data
                db.commit()
                add_log(db, task, f"SERP Research completed.", step="serp_research")
                save_step_result(db, task, "serp_research", result=json.dumps(serp_data.get("urls", []), ensure_ascii=False), status="completed")
            
            # ================================================================
            # Phase 2: Scraping Competitors
            # ================================================================
            if not task.competitors_text:
                urls = task.serp_data.get("urls", [])
                if not urls:
                    raise Exception("No URLs found in SERP data")
                
                add_log(db, task, f"Scraping {len(urls)} competitors...", step="competitor_scraping")
                save_step_result(db, task, "competitor_scraping", result=None, status="running")
            
                scrape_data = scrape_urls(urls)
                task.competitors_text = scrape_data["merged_text"]
            
                task.outline = {
                    "scrape_info": {
                        "avg_words": scrape_data["average_word_count"],
                        "headers": scrape_data["headers_structure"]
                    }
                }
                db.commit()
                add_log(db, task, f"Scraped competitors. Avg word count: {scrape_data['average_word_count']}", step="competitor_scraping")
                save_step_result(db, task, "competitor_scraping", result=f"Scraped URLs. Avg words: {scrape_data['average_word_count']}", status="completed")

            # ================================================================
            # Phase 3: Analysis (4 agents)
            # ================================================================
            if not task.outline or "final_outline" not in task.outline:
                outline_data = task.outline or {}
                scrape_info = outline_data.get("scrape_info", {})
                avg_words = scrape_info.get("avg_words", 800)
                headers_info = scrape_info.get("headers", [])
            
                paa = task.serp_data.get("paa", []) if task.serp_data else []
                related = task.serp_data.get("related_searches", []) if task.serp_data else []
                add_kw_text = f"\nAdditional Keywords: {task.additional_keywords}" if task.additional_keywords else ""
            
                base_context = (
                    f"Keyword: {task.main_keyword}{add_kw_text}\n"
                    f"Country: {task.country}\n"
                    f"Language: {task.language}\n"
                    f"People Also Ask: {json.dumps(paa, ensure_ascii=False)}\n"
                    f"Related Searches: {json.dumps(related, ensure_ascii=False)}\n"
                    f"Competitors Headers: {json.dumps(headers_info, ensure_ascii=False)}\n"
                    f"Target word count: {avg_words}"
                )
            
                # Basic vars available during analysis phase
                analysis_vars = {
                    "keyword": task.main_keyword,
                    "additional_keywords": task.additional_keywords or "",
                    "country": task.country,
                    "language": task.language,
                    "exclude_words": settings.EXCLUDE_WORDS,
                    "site_name": site_name,
                    "page_type": task.page_type,
                    "competitors_headers": json.dumps(headers_info, ensure_ascii=False),
                    "merged_markdown": task.competitors_text or "",
                    "avg_word_count": str(avg_words),
                }
            
                # 3a: AI анализ структуры
                add_log(db, task, "Starting AI Structure Analysis...", step="ai_structure_analysis")
                save_step_result(db, task, "ai_structure_analysis", result=None, status="running")
                ai_structure = call_agent(
                    db, "ai_structure_analysis", base_context, 
                    response_format={"type": "json_object"}, variables=analysis_vars
                )
                analysis_vars["result_ai_structure_analysis"] = ai_structure
            
                try:
                    ai_struct_data = json.loads(ai_structure)
                    analysis_vars["intent"] = ai_struct_data.get("intent", "")
                    analysis_vars["Taxonomy"] = ai_struct_data.get("Taxonomy", "")
                    analysis_vars["Attention"] = ai_struct_data.get("Attention", "")
                    analysis_vars["structura"] = ai_struct_data.get("structura", "")
                    outline_data["ai_structure_parsed"] = ai_struct_data
                except Exception as e:
                    add_log(db, task, f"Warning: Failed to parse ai_structure_analysis JSON: {e}", level="warn", step="ai_structure_analysis")
                    analysis_vars["intent"] = ""
                    analysis_vars["Taxonomy"] = ""
                    analysis_vars["Attention"] = ""
                    analysis_vars["structura"] = ""
                
                add_log(db, task, f"AI Structure Analysis completed ({len(ai_structure)} chars)", step="ai_structure_analysis")
                save_step_result(db, task, "ai_structure_analysis", result=ai_structure, status="completed")
            
                # 3b: Анализ кластера запросов для разработки "Чанков"
                add_log(db, task, "Starting Chunk Cluster Analysis...", step="chunk_cluster_analysis")
                save_step_result(db, task, "chunk_cluster_analysis", result=None, status="running")
                chunk_context = f"{base_context}\n\nAI Structure Analysis:\n{ai_structure}"
                chunk_analysis = call_agent(db, "chunk_cluster_analysis", chunk_context, variables=analysis_vars)
                analysis_vars["result_chunk_cluster_analysis"] = chunk_analysis
                add_log(db, task, f"Chunk Cluster Analysis completed ({len(chunk_analysis)} chars)", step="chunk_cluster_analysis")
                save_step_result(db, task, "chunk_cluster_analysis", result=chunk_analysis, status="completed")
            
                # 3c: Анализ структуры конкурентов
                add_log(db, task, "Starting Competitor Structure Analysis...", step="competitor_structure_analysis")
                save_step_result(db, task, "competitor_structure_analysis", result=None, status="running")
                competitor_context = (
                    f"{base_context}\n\n"
                    f"Competitors Text:\n{task.competitors_text[:20000]}\n\n"
                    f"Chunk Analysis:\n{chunk_analysis}"
                )
                competitor_structure = call_agent(db, "competitor_structure_analysis", competitor_context, variables=analysis_vars)
                analysis_vars["result_competitor_structure_analysis"] = competitor_structure
                add_log(db, task, f"Competitor Structure Analysis completed ({len(competitor_structure)} chars)", step="competitor_structure_analysis")
                save_step_result(db, task, "competitor_structure_analysis", result=competitor_structure, status="completed")
            
                # 3d: Финальный анализ структуры (produces final outline as JSON)
                add_log(db, task, "Starting Final Structure Analysis (JSON)...", step="final_structure_analysis")
                save_step_result(db, task, "final_structure_analysis", result=None, status="running")
                final_analysis_context = (
                    f"{base_context}\n\n"
                    f"AI Structure Analysis:\n{ai_structure}\n\n"
                    f"Chunk Analysis:\n{chunk_analysis}\n\n"
                    f"Competitor Structure Analysis:\n{competitor_structure}"
                )
                outline_json_str = call_agent(
                    db, "final_structure_analysis", final_analysis_context,
                    response_format={"type": "json_object"}, variables=analysis_vars
                )
                add_log(db, task, f"Final Structure Analysis completed", step="final_structure_analysis")
                save_step_result(db, task, "final_structure_analysis", result=outline_json_str, status="completed")
            
                outline_data["final_outline"] = json.loads(outline_json_str)
                outline_data["ai_structure"] = ai_structure
                outline_data["chunk_analysis"] = chunk_analysis
                outline_data["competitor_structure"] = competitor_structure
                outline_data["final_structure"] = outline_json_str
                outline_data["fiinal_structure"] = outline_json_str
                task.outline = outline_data
                db.commit()
        else:
            if not task.outline:
                task.serp_data = {}
                task.competitors_text = ""
                task.outline = {"final_outline": {"page_title": page_title, "sections": []}}
                db.commit()

        # ================================================================
        # Phase 4: Author context
        # ================================================================
        author_style = ""
        imitation = ""
        year = ""
        face = ""
        target_audience = ""
        rhythms_style = ""
        
        if task.author_id:
            author = db.query(Author).filter(Author.id == task.author_id).first()
            if author:
                author_style = author.style_prompt or ""
                imitation = author.imitation or ""
                year = author.year or ""
                face = author.face or ""
                target_audience = author.target_audience or ""
                rhythms_style = author.rhythms_style or ""

        author_block = (
            f"Author Style/Text Block: {author_style}\n"
            f"Imitation (Mimicry): {imitation}\n"
            f"Year: {year}\n"
            f"Face: {face}\n"
            f"Target Audience: {target_audience}\n"
            f"Rhythms & Style: {rhythms_style}\n"
            f"Exclude Words: {settings.EXCLUDE_WORDS}"
        )
        
        # Build template variables dict for {{variable}} substitution in prompts
        author_name = ""
        if task.author_id:
            author = db.query(Author).filter(Author.id == task.author_id).first()
            if author:
                author_name = author.author or ""
        
        template_vars = {
            "keyword": task.main_keyword,
            "additional_keywords": task.additional_keywords or "",
            "country": task.country,
            "language": task.language,
            "page_type": task.page_type,
            "competitors_headers": json.dumps(task.outline.get('scrape_info', {}).get('headers', []), ensure_ascii=False),
            "merged_markdown": task.competitors_text or "",
            "avg_word_count": str(task.outline.get('scrape_info', {}).get('avg_words', 800)),
            "author": author_name,
            "author_style": author_style,
            "imitation": imitation,
            "target_audience": target_audience,
            "face": face,
            "year": year,
            "rhythms_style": rhythms_style,
            "exclude_words": settings.EXCLUDE_WORDS,
            "site_name": site_name,
            # Results from analysis phase (loaded from saved outline)
            "result_ai_structure_analysis": task.outline.get("ai_structure", ""),
            "intent": task.outline.get("ai_structure_parsed", {}).get("intent", ""),
            "Taxonomy": task.outline.get("ai_structure_parsed", {}).get("Taxonomy", ""),
            "Attention": task.outline.get("ai_structure_parsed", {}).get("Attention", ""),
            "structura": task.outline.get("ai_structure_parsed", {}).get("structura", ""),
            "result_chunk_cluster_analysis": task.outline.get("chunk_analysis", ""),
            "result_competitor_structure_analysis": task.outline.get("competitor_structure", ""),
            "result_final_structure_analysis": task.outline.get("final_structure", json.dumps(task.outline.get("final_outline", {}), ensure_ascii=False)),
            "page_slug": page_slug,
            "page_title": page_title,
            "all_site_pages": json.dumps(all_site_pages, ensure_ascii=False),
        }
        
        outline_json = task.outline.get("final_outline", {})

        # ================================================================
        # Phase 5: Первичная генерация (primary_generation)
        # ================================================================
        gen_context = (
            f"Keyword: {task.main_keyword}\n"
            f"Language: {task.language}\n"
            f"{author_block}\n"
            f"Outline: {json.dumps(outline_json, ensure_ascii=False)}"
        )
        add_log(db, task, "Starting Primary Generation...", step="primary_generation")
        save_step_result(db, task, "primary_generation", result=None, status="running")
        draft_html = call_agent(db, "primary_generation", gen_context, variables=template_vars)
        template_vars["result_primary_generation"] = draft_html
        add_log(db, task, f"Primary Generation completed ({len(draft_html)} chars)", step="primary_generation")
        save_step_result(db, task, "primary_generation", result=draft_html, status="completed")

        # Phase 6-9 are skipped if use_serp is False
        if use_serp:
            # ================================================================
            # Phase 6: Лучше ли наша статья конкурентов? (competitor_comparison)
            # ================================================================
            comparison_context = (
                f"Our article:\n{draft_html}\n\n"
                f"Competitors:\n{task.competitors_text[:15000]}"
            )
            add_log(db, task, "Starting Competitor Comparison...", step="competitor_comparison")
            save_step_result(db, task, "competitor_comparison", result=None, status="running")
            comparison_review = call_agent(db, "competitor_comparison", comparison_context, variables=template_vars)
            template_vars["result_competitor_comparison"] = comparison_review
            add_log(db, task, f"Competitor Comparison completed", step="competitor_comparison")
            save_step_result(db, task, "competitor_comparison", result=comparison_review, status="completed")

            # ================================================================
            # Phase 7: Мнение читателя (reader_opinion)
            # ================================================================
            reader_context = f"Article:\n{draft_html}"
            add_log(db, task, "Starting Reader Opinion analysis...", step="reader_opinion")
            save_step_result(db, task, "reader_opinion", result=None, status="running")
            reader_feedback = call_agent(db, "reader_opinion", reader_context, variables=template_vars)
            template_vars["result_reader_opinion"] = reader_feedback
            add_log(db, task, f"Reader Opinion completed", step="reader_opinion")
            save_step_result(db, task, "reader_opinion", result=reader_feedback, status="completed")

            # ================================================================
            # Phase 8: Перелинковка и цитаты (interlinking_citations)
            # ================================================================
            interlink_context = (
                f"Article:\n{draft_html}\n\n"
                f"Keyword: {task.main_keyword}\n"
                f"Language: {task.language}\n"
                f"Site: {site_name}"
            )
            add_log(db, task, "Starting Interlinking & Citations...", step="interlinking_citations")
            save_step_result(db, task, "interlinking_citations", result=None, status="running")
            interlink_suggestions = call_agent(db, "interlinking_citations", interlink_context, variables=template_vars)
            template_vars["result_interlinking_citations"] = interlink_suggestions
            add_log(db, task, f"Interlinking & Citations completed", step="interlinking_citations")
            save_step_result(db, task, "interlinking_citations", result=interlink_suggestions, status="completed")

            # ================================================================
            # Phase 9: Улучшайзер (improver)
            # ================================================================
            improver_context = (
                f"Draft:\n{draft_html}\n\n"
                f"Competitor Comparison Review:\n{comparison_review}\n\n"
                f"Reader Feedback:\n{reader_feedback}\n\n"
                f"Interlinking & Citations Suggestions:\n{interlink_suggestions}"
            )
            add_log(db, task, "Starting Improver (draft enhancement)...", step="improver")
            save_step_result(db, task, "improver", result=None, status="running")
            improved_html = call_agent(db, "improver", improver_context, variables=template_vars)
            template_vars["result_improver"] = improved_html
            add_log(db, task, f"Improver completed ({len(improved_html)} chars)", step="improver")
            save_step_result(db, task, "improver", result=improved_html, status="completed")
        else:
            improved_html = draft_html

        # ================================================================
        # Phase 10: Финальная редактура и сверка (final_editing)
        # ================================================================
        editing_context = (
            f"Improved HTML:\n{improved_html}\n\n"
            f"Original Outline:\n{json.dumps(outline_json, ensure_ascii=False)}\n\n"
            f"Review & verify this HTML article matches the outline structure."
        )
        add_log(db, task, "Starting Final Editing...", step="final_editing")
        save_step_result(db, task, "final_editing", result=None, status="running")
        final_html = call_agent(db, "final_editing", editing_context, variables=template_vars)
        template_vars["result_final_editing"] = final_html
        add_log(db, task, f"Final Editing completed ({len(final_html)} chars)", step="final_editing")
        save_step_result(db, task, "final_editing", result=final_html, status="completed")

        # ================================================================
        # Phase 11: Структура HTML (html_structure)
        # ================================================================
        html_struct_context = (
            f"Article HTML:\n{final_html}\n\n"
            f"Keyword: {task.main_keyword}\n"
            f"Language: {task.language}"
        )
        add_log(db, task, "Starting HTML Structure formatting...", step="html_structure")
        save_step_result(db, task, "html_structure", result=None, status="running")
        final_html = call_agent(db, "html_structure", html_struct_context, variables=template_vars)
        template_vars["result_html_structure"] = final_html
        add_log(db, task, f"HTML Structure completed ({len(final_html)} chars)", step="html_structure")
        save_step_result(db, task, "html_structure", result=final_html, status="completed")

        # ================================================================
        # Phase 12: Генерация мета-тегов (meta_generation)
        # ================================================================
        meta_context = f"Article HTML:\n{final_html}"
        add_log(db, task, "Generating Meta Tags (JSON)...", step="meta_generation")
        save_step_result(db, task, "meta_generation", result=None, status="running")
        meta_json_str = call_agent(
            db, "meta_generation", meta_context,
            response_format={"type": "json_object"}, variables=template_vars
        )
        add_log(db, task, f"Meta Tags Generation completed", step="meta_generation")
        save_step_result(db, task, "meta_generation", result=meta_json_str, status="completed")
        try:
            meta_data = json.loads(meta_json_str)
            title = meta_data.get("title", f"{task.main_keyword} Guide")
            description = meta_data.get("description", "")
        except:
            title = task.main_keyword.title()
            description = f"Read our comprehensive guide about {task.main_keyword}."

        word_count = len(BeautifulSoup(final_html, "html.parser").get_text(strip=True).split())

        # ================================================================
        # Phase 13: Template Injection & Save
        # ================================================================
        full_page = generate_full_page(db, str(task.target_site_id), final_html, title, description)

        article = GeneratedArticle(
            task_id=task.id,
            title=title,
            description=description,
            html_content=final_html,
            full_page_html=full_page,
            word_count=word_count
        )
        db.add(article)

        task.status = "completed"
        db.commit()
        
        add_log(db, task, "✅ Pipeline finished successfully", step=None)
        notify_task_success(str(task.id), task.main_keyword, site_name, word_count)

    except Exception as e:
        task.status = "failed"
        task.error_log = traceback.format_exc()
        db.commit()
        add_log(db, task, f"❌ Pipeline failed: {str(e)}", level="error", step=None)
        notify_task_failed(str(task.id), task.main_keyword, str(e), site_name)
