import datetime
import html
import re

from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.project import SiteProject
from app.models.site import Site
from app.models.template import Template


def ensure_head_meta(html_in: str, title: str, description: str) -> str:
    """
    Ensures <title> and <meta name="description"> exist in <head>.
    - Full document: updates first <title> / first meta description, or injects after <head>.
    - Fragment (no <html> or no <head>): wraps with minimal HTML document.
    - Empty title: does not add or replace <title>.
    - Empty description: does not add or replace meta description.
    Values are HTML-escaped.
    """
    raw = html_in or ""
    title_esc = html.escape(title or "", quote=True)
    desc_esc = html.escape(description or "", quote=True)

    has_html_tag = bool(re.search(r"<html[\s>]", raw, re.IGNORECASE))
    has_head_tag = bool(re.search(r"<head[\s>]", raw, re.IGNORECASE))

    if not has_html_tag or not has_head_tag:
        parts = [
            "<!doctype html>\n<html>\n<head>\n",
            '<meta charset="utf-8">\n',
        ]
        if title:
            parts.append(f"<title>{title_esc}</title>\n")
        if description:
            parts.append(f'<meta name="description" content="{desc_esc}">\n')
        parts.extend(["</head>\n<body>\n", raw, "\n</body>\n</html>\n"])
        return "".join(parts)

    out = raw
    if title:
        if re.search(r"<title>.*?</title>", out, flags=re.IGNORECASE | re.DOTALL):
            out = re.sub(
                r"<title>.*?</title>",
                f"<title>{title_esc}</title>",
                out,
                count=1,
                flags=re.IGNORECASE | re.DOTALL,
            )
        else:
            out = re.sub(
                r"(<head[^>]*>)",
                r"\1\n<title>" + title_esc + "</title>",
                out,
                count=1,
                flags=re.IGNORECASE,
            )

    if description:
        if re.search(
            r'<meta\s+[^>]*name\s*=\s*["\']description["\'][^>]*>',
            out,
            flags=re.IGNORECASE,
        ):
            out = re.sub(
                r'<meta\s+[^>]*name\s*=\s*["\']description["\'][^>]*(?:/\s*)?>',
                f'<meta name="description" content="{desc_esc}">',
                out,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            out = re.sub(
                r"(<head[^>]*>)",
                r"\1\n" + f'<meta name="description" content="{desc_esc}">',
                out,
                count=1,
                flags=re.IGNORECASE,
            )

    return out


def render_author_footer(author: Author | None) -> str:
    """
    HTML block with author data for the end of <body>.
    Returns "" if no author or all display fields empty. Values are HTML-escaped.
    """
    if not author:
        return ""
    rows = [
        ("Автор", author.author),
        ("Страна", author.country_full),
        ("Код страны", author.co_short),
        ("Город", author.city),
        ("Язык", author.language),
        ("Биография", author.bio),
    ]
    rows = [(k, v) for k, v in rows if v and str(v).strip()]
    if not rows:
        return ""
    items = "\n".join(f"  <li><strong>{html.escape(k)}:</strong> {html.escape(str(v))}</li>" for k, v in rows)
    return (
        '\n<section class="author-info" aria-label="Об авторе">\n'
        "  <h2>Об авторе</h2>\n"
        f"  <ul>\n{items}\n  </ul>\n"
        "</section>\n"
    )


def generate_full_page(
    db: Session,
    site_id: str,
    html_content: str,
    title: str,
    description: str,
    project_id: str | None = None,
) -> str | None:
    """
    Uses the site's assigned Template (if any) to wrap generated content.
    Returns the full HTML page or None if no template is linked or project disables wrapper.
    """
    if project_id:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if project and not getattr(project, "use_site_template", True):
            return None

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site or not site.template_id:
        return None

    selected_template = (
        db.query(Template)
        .filter(Template.id == site.template_id, Template.is_active == True)  # noqa: E712
        .first()
    )
    if not selected_template:
        return None

    full_html = selected_template.html_template

    replacements = {
        "{content}": html_content,
        "{{content}}": html_content,
        "<!-- CONTENT -->": html_content,
        "{title}": title,
        "{{title}}": title,
        "<!-- TITLE -->": title,
        "{description}": description,
        "{{description}}": description,
        "<!-- DESCRIPTION -->": description,
        "{year}": str(datetime.datetime.now().year),
    }

    for placeholder, new_val in replacements.items():
        if placeholder in full_html:
            full_html = full_html.replace(placeholder, new_val)

    if (
        "<title>" in full_html
        and "</title>" in full_html
        and "{" not in full_html.split("<title>")[1].split("</title>")[0]
    ):
        full_html = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", full_html, flags=re.IGNORECASE)

    if '<meta name="description"' in full_html:
        full_html = re.sub(
            r'<meta\s+name=["\']description["\']\s+content=["\'].*?["\']\s*/?>',
            f'<meta name="description" content="{description}">',
            full_html,
            flags=re.IGNORECASE,
        )

    db.commit()
    return full_html


def get_template_for_reference(db: Session, site_id: str) -> tuple[str | None, str | None]:
    """
    Returns HTML template and name for LLM prompts (site.template_id → Template).
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site or not site.template_id:
        return (None, None)

    t = (
        db.query(Template)
        .filter(Template.id == site.template_id, Template.is_active == True)  # noqa: E712
        .first()
    )
    if not t:
        return (None, None)
    return (t.html_template, t.name)
