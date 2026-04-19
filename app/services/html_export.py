"""
HTML export for MODX paste: resolve article body with same priority as DOCX/pipeline,
optional cleanup stripping site chrome while preserving <!-- MEDIA: ... --> comments.
"""
from __future__ import annotations

import io
import re
import zipfile
from html import escape
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

_HTML_BLOCK = re.compile(
    r"<(h[1-6]|p|ul|ol|li|table|div|section|article|br|blockquote)\b",
    re.IGNORECASE,
)


def is_html_content(text: str) -> bool:
    if not text or not text.strip():
        return False
    return bool(_HTML_BLOCK.search(text))


EXPORT_STEP_ORDER = (
    "image_inject",
    "html_structure",
    "final_editing",
    "improver",
    "interlinking_citations",
    "reader_opinion",
    "competitor_comparison",
    "primary_generation",
    "primary_generation_about",
    "primary_generation_legal",
)


class HtmlExportNotReadyError(Exception):
    """Raised when final_editing holds non-HTML (e.g. markdown) for strict HTML export."""

    def __init__(self, message: str = "Page not ready for HTML export") -> None:
        super().__init__(message)
        self.message = message


def extract_inner_from_full_page(html: str) -> str:
    """Prefer <main>, then <article>, then <body> inner HTML; else return stripped input."""
    s = (html or "").strip()
    if not s:
        return ""
    soup = BeautifulSoup(s, "html.parser")
    for tag in ("main", "article", "body"):
        el = soup.find(tag)
        if el:
            inner = el.decode_contents()
            return inner if inner is not None else ""
    return s


def resolve_export_body(
    task: Any,
    article: Any,
    *,
    for_html_export: bool = False,
) -> Tuple[str, str]:
    """
    Return (body, source_key). Same priority as DOCX / pick_structured_html_for_assembly order
    for step_results; article.html_content and extracted full_page_html first.

    If for_html_export and final_editing has non-empty non-HTML content, raises HtmlExportNotReadyError.
    """
    if article:
        hc = (article.html_content or "").strip()
        if hc:
            return (str(article.html_content), "article.html_content")

        fp = (article.full_page_html or "").strip()
        if fp:
            extracted = extract_inner_from_full_page(str(article.full_page_html))
            if extracted.strip():
                return (extracted, "article.full_page_html")

    if not task:
        return ("", "none")

    sr = task.step_results or {}
    for key in EXPORT_STEP_ORDER:
        step = sr.get(key)
        if not isinstance(step, dict):
            continue
        raw = str(step.get("result") or "")
        if not raw.strip():
            continue
        if key == "final_editing" and for_html_export and not is_html_content(raw):
            raise HtmlExportNotReadyError("Page not ready for HTML export")
        return (raw, f"step:{key}")

    return ("", "none")


def resolve_export_html(task: Any, article: Any) -> str:
    """Resolved body + clean_html_for_paste for download/paste."""
    body, _source = resolve_export_body(task, article, for_html_export=True)
    if not body.strip():
        raise ValueError("No HTML content to export")
    return clean_html_for_paste(body)


def clean_html_for_paste(html: str, *, drop_doctype: bool = True) -> str:
    """
    Light cleanup: unwrap main/article/body, strip site chrome, preserve HTML comments.
    """
    raw = html or ""
    if not raw.strip():
        return ""

    soup = BeautifulSoup(raw, "html.parser")

    if drop_doctype:
        for decl in list(soup.contents):
            if str(type(decl).__name__) == "Doctype":
                decl.extract()

    inner = soup.find("main") or soup.find("article") or soup.find("body")
    if inner is not None:
        inner_html = inner.decode_contents()
        soup = BeautifulSoup(inner_html, "html.parser")

    for sel in ("nav", "header", "footer", "script", "style", "link", "meta", "title"):
        for t in soup.find_all(sel):
            t.decompose()

    top_nodes: List[Tag] = [t for t in soup.children if isinstance(t, Tag)]
    for node in top_nodes:
        if node.get("style"):
            del node["style"]
        cls = node.get("class")
        if isinstance(cls, list) and cls:
            rest = [c for c in cls if not str(c).startswith("Mso")]
            if rest:
                node["class"] = rest
            else:
                del node["class"]
        elif isinstance(cls, str) and cls.startswith("Mso"):
            del node["class"]

    out = soup.decode(formatter="html5")
    return out.strip()


def sanitize_filename_component(s: str) -> str:
    t = (s or "").strip().replace("/", "_").replace("\\", "_")
    out = "".join(c for c in t if c.isalnum() or c in " -_") or "page"
    return out.strip().replace(" ", "_")[:200]


def html_filename_for_task(task: Any, page_slug: Optional[str] = None) -> str:
    base = (page_slug or "").strip() or (task.main_keyword or "page")
    return f"{sanitize_filename_component(base)}.html"


def build_project_html_zip(db: Session, project_id: str) -> bytes:
    from app.models.article import GeneratedArticle
    from app.models.blueprint import BlueprintPage
    from app.models.project import SiteProject
    from app.models.task import Task

    project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
    if not project:
        raise ValueError("Project not found")

    pages: List[BlueprintPage] = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.blueprint_id == project.blueprint_id)
        .order_by(BlueprintPage.sort_order)
        .all()
    )
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    by_bp: Dict[str, Task] = {}
    for t in tasks:
        if t.blueprint_page_id:
            by_bp[str(t.blueprint_page_id)] = t

    task_ids = [t.id for t in tasks]
    articles_by_task: Dict[str, GeneratedArticle] = {}
    if task_ids:
        arts = db.query(GeneratedArticle).filter(GeneratedArticle.task_id.in_(task_ids)).all()
        for a in arts:
            articles_by_task[str(a.task_id)] = a

    buf = io.BytesIO()
    toc_rows: List[Tuple[str, str]] = []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for bp in pages:
            task = by_bp.get(str(bp.id))
            if not task or task.status != "completed":
                continue
            article = articles_by_task.get(str(task.id))
            try:
                html = resolve_export_html(task, article)
            except (HtmlExportNotReadyError, ValueError):
                continue
            fname = html_filename_for_task(task, bp.page_slug)
            zf.writestr(fname, html.encode("utf-8"))
            title = (article.title if article else None) or task.main_keyword or fname
            toc_rows.append((fname, title))

        if not toc_rows:
            raise ValueError("No completed pages to export")

        items = "".join(
            f'<li><a href="{escape(fn)}">{escape(tit)}</a></li>' for fn, tit in toc_rows
        )
        index_html = (
            "<!DOCTYPE html>\n"
            '<html lang="en"><head><meta charset="utf-8">'
            f"<title>{escape(project.name)} — TOC</title></head><body>\n"
            f"<h1>{escape(project.name)}</h1>\n<ul>\n{items}\n</ul>\n</body></html>\n"
        )
        zf.writestr("index.html", index_html.encode("utf-8"))

    return buf.getvalue()


def build_project_html_concat(db: Session, project_id: str) -> str:
    from app.models.article import GeneratedArticle
    from app.models.blueprint import BlueprintPage
    from app.models.project import SiteProject
    from app.models.task import Task

    project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
    if not project:
        raise ValueError("Project not found")

    pages: List[BlueprintPage] = (
        db.query(BlueprintPage)
        .filter(BlueprintPage.blueprint_id == project.blueprint_id)
        .order_by(BlueprintPage.sort_order)
        .all()
    )
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    by_bp: Dict[str, Task] = {}
    for t in tasks:
        if t.blueprint_page_id:
            by_bp[str(t.blueprint_page_id)] = t

    task_ids = [t.id for t in tasks]
    articles_by_task: Dict[str, GeneratedArticle] = {}
    if task_ids:
        arts = db.query(GeneratedArticle).filter(GeneratedArticle.task_id.in_(task_ids)).all()
        for a in arts:
            articles_by_task[str(a.task_id)] = a

    parts: List[str] = []
    for bp in pages:
        task = by_bp.get(str(bp.id))
        if not task or task.status != "completed":
            continue
        article = articles_by_task.get(str(task.id))
        try:
            html = resolve_export_html(task, article)
        except (HtmlExportNotReadyError, ValueError):
            continue
        slug = sanitize_filename_component((bp.page_slug or "").strip() or task.main_keyword or "page")
        parts.append(f"<!-- ===== PAGE: {slug} ===== -->\n{html}")

    if not parts:
        raise ValueError("No completed pages to export")

    return "\n\n".join(parts)

