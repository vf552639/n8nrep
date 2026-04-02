import datetime
import re
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.site import Site
from app.models.template import Template


def generate_full_page(db: Session, site_id: str, html_content: str, title: str, description: str) -> Optional[str]:
    """
    Uses the site's assigned Template (if any) to wrap generated content.
    Returns the full HTML page or None if no template is linked.
    """
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

    if "<title>" in full_html and "</title>" in full_html and "{" not in full_html.split("<title>")[1].split("</title>")[0]:
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


def get_template_for_reference(db: Session, site_id: str) -> Tuple[Optional[str], Optional[str]]:
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
