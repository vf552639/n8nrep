import json

from app.config import settings
from app.models.article import GeneratedArticle
from app.models.author import Author
from app.services.deduplication import ContentDeduplicator
from app.services.json_parser import clean_and_parse_json
from app.services.meta_parser import extract_meta_from_parsed
from app.services.pipeline.context import PipelineContext
from app.services.pipeline.errors import ParseError, ValidationError
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


def _extract_meta_with_fallback(ctx: PipelineContext) -> tuple[dict, str, str]:
    meta_json_str = ctx.task.step_results.get(STEP_META_GEN, {}).get("result", "{}")
    if not isinstance(meta_json_str, str):
        meta_json_str = json.dumps(meta_json_str, ensure_ascii=False) if meta_json_str else "{}"
    meta_data = clean_and_parse_json(meta_json_str)
    if meta_json_str and not meta_data:
        raise ParseError("meta_generation returned unparseable JSON")

    add_log(
        ctx.db,
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
        ctx.db,
        ctx.task,
        f"meta extracted: title='{title[:80]}', desc='{description[:80]}', h1='{h1_meta[:80]}'",
        level="debug",
        step=STEP_META_GEN,
    )
    if not title:
        title = ctx.task.main_keyword.title()
        add_log(
            ctx.db,
            ctx.task,
            "⚠️ meta_generation не вернул Title — fallback на keyword",
            level="warn",
            step=STEP_META_GEN,
        )
    return meta_data, title, description


def _build_full_page(ctx: PipelineContext, structured_html: str, title: str, description: str) -> str:
    full_page = generate_full_page(
        ctx.db,
        str(ctx.task.target_site_id),
        structured_html,
        title,
        description,
        project_id=str(ctx.task.project_id) if ctx.task.project_id else None,
    )
    return ensure_head_meta(
        structured_html if full_page is None else full_page,
        title,
        description,
    )


def _apply_author_footer(db, task, full_page: str) -> str:
    author_obj = db.query(Author).filter(Author.id == task.author_id).first() if task.author_id else None
    author_html = render_author_footer(author_obj)
    if not author_html:
        return full_page
    if "</body>" in full_page:
        return full_page.replace("</body>", author_html + "\n</body>", 1)
    return full_page + author_html


def _process_fact_check(ctx: PipelineContext) -> tuple[str, list, bool]:
    fact_check_status_val = ""
    fact_check_issues_val = []
    needs_review_val = False
    if not settings.FACT_CHECK_ENABLED:
        return fact_check_status_val, fact_check_issues_val, needs_review_val

    fc_res_str = ctx.task.step_results.get(STEP_CONTENT_FACT_CHECK, {}).get("result", "{}")
    if not fc_res_str:
        return fact_check_status_val, fact_check_issues_val, needs_review_val
    fc_data = clean_and_parse_json(fc_res_str)
    if not fc_data:
        return fact_check_status_val, fact_check_issues_val, needs_review_val

    fact_check_status_val = fc_data.get("verification_status", "")
    fact_check_issues_val = fc_data.get("issues", [])
    critical_count = sum(1 for issue in fact_check_issues_val if issue.get("severity") == "critical")
    if fact_check_status_val == "fail" or critical_count >= settings.FACT_CHECK_FAIL_THRESHOLD:
        needs_review_val = True
        add_log(
            ctx.db,
            ctx.task,
            f"Fact-check marked for review ({critical_count} critical issues).",
            level="warn",
            step=STEP_CONTENT_FACT_CHECK,
        )
        if getattr(settings, "FACT_CHECK_MODE", "soft") == "strict":
            raise ValidationError("Fact-check failed in strict mode. Task aborted.")
    elif fact_check_status_val == "warn":
        add_log(
            ctx.db,
            ctx.task,
            "Fact-check returned warnings.",
            level="warn",
            step=STEP_CONTENT_FACT_CHECK,
        )
    return fact_check_status_val, fact_check_issues_val, needs_review_val


def _upsert_article(
    ctx: PipelineContext,
    *,
    title: str,
    description: str,
    meta_data: dict,
    structured_html: str,
    full_page: str,
    word_count: int,
    fact_check_status: str,
    fact_check_issues: list,
    needs_review: bool,
) -> GeneratedArticle:
    existing = ctx.db.query(GeneratedArticle).filter(GeneratedArticle.task_id == ctx.task.id).first()
    if not existing:
        article = GeneratedArticle(task_id=ctx.task.id)
        ctx.db.add(article)
    else:
        article = existing
    article.title = title
    article.description = description
    article.meta_data = meta_data
    article.html_content = structured_html
    article.full_page_html = full_page
    article.word_count = word_count
    article.fact_check_status = fact_check_status
    article.fact_check_issues = fact_check_issues
    article.needs_review = needs_review
    return article


def _save_dedup_anchors(ctx: PipelineContext, html: str) -> None:
    if not ctx.task.project_id:
        return
    deduplicator = ContentDeduplicator(ctx.db)
    anchors = deduplicator.extract_anchors(
        article_html=html, task_id=str(ctx.task.id), keyword=ctx.task.main_keyword
    )
    deduplicator.save_anchors(project_id=str(ctx.task.project_id), task_id=str(ctx.task.id), anchors=anchors)


def finalize_article(ctx: PipelineContext) -> GeneratedArticle:
    """Assemble and persist article, then return the upserted row.

    Raises:
        ParseError: If `meta_generation` output is present but not valid JSON.
        ValidationError: If HTML body is empty or strict fact-check fails.
        Exception: DB/template and other unexpected assembly errors.
    """
    db = ctx.db
    add_log(db, ctx.task, "Starting article assembly and saving...", step=None)
    structured_html = pick_structured_html_for_assembly(ctx)
    if not structured_html.strip():
        raise ValidationError("No HTML body produced by pipeline steps — cannot assemble article.")

    meta_data, title, description = _extract_meta_with_fallback(ctx)
    word_count = count_content_words(structured_html)
    full_page = _build_full_page(ctx, structured_html, title, description)
    full_page = _apply_author_footer(db, ctx.task, full_page)
    fact_check_status, fact_check_issues, needs_review = _process_fact_check(ctx)
    article = _upsert_article(
        ctx,
        title=title,
        description=description,
        meta_data=meta_data,
        structured_html=structured_html,
        full_page=full_page,
        word_count=word_count,
        fact_check_status=fact_check_status,
        fact_check_issues=fact_check_issues,
        needs_review=needs_review,
    )
    _save_dedup_anchors(ctx, structured_html)
    ctx.task.status = "completed"
    db.commit()
    return article
