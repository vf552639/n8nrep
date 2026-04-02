import json
from typing import Any

from app.models.site import Site
from app.models.template import LegalPageTemplate, LEGAL_PAGE_TYPES


def substitute_legal_html(html: str, legal_info: dict[str, Any]) -> str:
    if not html:
        return ""
    out = html
    for key, val in (legal_info or {}).items():
        for pat in (f"{{{{{key}}}}}", f"{{{{ {key} }}}}"):
            out = out.replace(pat, str(val))
    return out


def inject_legal_template_vars(ctx: Any) -> None:
    """Fill legal_reference_html and legal_variables when SERP is off and page is a legal type."""
    ctx.template_vars["legal_reference_html"] = ""
    ctx.template_vars["legal_variables"] = "{}"

    if ctx.use_serp:
        return
    if ctx.task.page_type not in LEGAL_PAGE_TYPES:
        return

    site = ctx.db.query(Site).filter(Site.id == ctx.task.target_site_id).first()
    if not site:
        return

    country = (site.country or "").strip().upper()
    lp = (
        ctx.db.query(LegalPageTemplate)
        .filter(
            LegalPageTemplate.country == country,
            LegalPageTemplate.page_type == ctx.task.page_type,
            LegalPageTemplate.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not lp:
        return

    legal_info = site.legal_info if isinstance(site.legal_info, dict) else {}
    html = substitute_legal_html(lp.html_content or "", legal_info)
    ctx.template_vars["legal_reference_html"] = html

    merged: dict[str, Any] = {}
    if isinstance(lp.variables, dict):
        merged.update(lp.variables)
    merged.update(legal_info)
    ctx.template_vars["legal_variables"] = json.dumps(merged, ensure_ascii=False)
