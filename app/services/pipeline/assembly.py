import json
import traceback

from app.config import settings
from app.models.article import GeneratedArticle
from app.models.author import Author
from app.services.deduplication import ContentDeduplicator
from app.services.json_parser import clean_and_parse_json
from app.services.meta_parser import extract_meta_from_parsed
from app.services.notifier import notify_task_failed, notify_task_success
from app.services.pipeline.context import PipelineContext
from app.services.pipeline.persistence import add_log, completed_step_body
from app.services.pipeline_constants import (
    STEP_COMP_COMPARISON,
    STEP_CONTENT_FACT_CHECK,
    STEP_FINAL_EDIT,
    STEP_HTML_STRUCT,
    STEP_IMAGE_INJECT,
    STEP_IMPROVER,
    STEP_INTERLINK,
    STEP_META_GEN,
    STEP_PRIMARY_GEN,
    STEP_PRIMARY_GEN_ABOUT,
    STEP_PRIMARY_GEN_LEGAL,
    STEP_READER_OPINION,
)
from app.services.template_engine import ensure_head_meta, generate_full_page, render_author_footer
from app.services.word_counter import count_content_words


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
        body = completed_step_body(ctx.task, key)
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
        body = completed_step_body(ctx.task, key)
        if body:
            return body
    return ""


def finalize_article(ctx: PipelineContext):
    db = ctx.db
    try:
        add_log(db, ctx.task, "Starting article assembly and saving...", step=None)
        structured_html = pick_structured_html_for_assembly(ctx)
        if not structured_html.strip():
            raise ValueError("No HTML body produced by pipeline steps — cannot assemble article.")
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

        full_page = ensure_head_meta(
            structured_html if full_page is None else full_page,
            title,
            description,
        )

        author_obj = (
            db.query(Author).filter(Author.id == ctx.task.author_id).first() if ctx.task.author_id else None
        )
        author_html = render_author_footer(author_obj)
        if author_html:
            if "</body>" in full_page:
                full_page = full_page.replace("</body>", author_html + "\n</body>", 1)
            else:
                full_page = full_page + author_html

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

                    critical_count = sum(
                        1 for issue in fact_check_issues_val if issue.get("severity") == "critical"
                    )

                    if fact_check_status_val == "fail" or critical_count >= settings.FACT_CHECK_FAIL_THRESHOLD:
                        needs_review_val = True
                        add_log(
                            db,
                            ctx.task,
                            f"Fact-check marked for review ({critical_count} critical issues).",
                            level="warn",
                            step=STEP_CONTENT_FACT_CHECK,
                        )

                        if getattr(settings, "FACT_CHECK_MODE", "soft") == "strict":
                            raise Exception("Fact-check failed in strict mode. Task aborted.")
                    elif fact_check_status_val == "warn":
                        add_log(
                            db,
                            ctx.task,
                            "Fact-check returned warnings.",
                            level="warn",
                            step=STEP_CONTENT_FACT_CHECK,
                        )

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
                article_html=structured_html, task_id=str(ctx.task.id), keyword=ctx.task.main_keyword
            )
            deduplicator.save_anchors(
                project_id=str(ctx.task.project_id), task_id=str(ctx.task.id), anchors=anchors
            )

        ctx.task.status = "completed"
        db.commit()

        add_log(db, ctx.task, "✅ Pipeline finished successfully", step=None)
        notify_task_success(str(ctx.task.id), ctx.task.main_keyword, ctx.site_name, word_count)

    except Exception as save_err:
        db.rollback()
        add_log(db, ctx.task, f"❌ Error saving article: {save_err!s}", level="error", step=None)
        ctx.task.status = "failed"
        ctx.task.error_log = traceback.format_exc()
        db.commit()
        notify_task_failed(str(ctx.task.id), ctx.task.main_keyword, str(save_err), ctx.site_name)
