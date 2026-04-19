import json
from typing import Any

from app.models.blueprint import BlueprintPage
from app.models.site import Site
from app.models.template import LegalPageTemplate, LEGAL_PAGE_TYPES

PAGE_TYPE_LABELS = {
    "privacy_policy": "Privacy Policy",
    "terms_and_conditions": "Terms & Conditions",
    "cookie_policy": "Cookie Policy",
    "responsible_gambling": "Responsible Gambling",
    "about_us": "About Us",
}


def page_type_label_for(page_type: str | None) -> str:
    if not page_type:
        return ""
    if page_type in PAGE_TYPE_LABELS:
        return PAGE_TYPE_LABELS[page_type]
    return str(page_type).replace("_", " ").title()


def substitute_legal_html(content: str, legal_info: dict[str, Any]) -> str:
    if not content:
        return ""
    out = content
    for key, val in (legal_info or {}).items():
        for pat in (f"{{{{{key}}}}}", f"{{{{ {key} }}}}"):
            out = out.replace(pat, str(val))
    return out


def inject_legal_template_vars(ctx: Any) -> None:
    """Fill legal reference, format, notes, variables for legal pages (non-SERP path)."""
    ctx.template_vars["legal_reference"] = ""
    ctx.template_vars["legal_reference_html"] = ""
    ctx.template_vars["legal_reference_format"] = "text"
    ctx.template_vars["legal_template_notes"] = ""
    ctx.template_vars["legal_variables"] = "{}"

    if ctx.task.page_type not in LEGAL_PAGE_TYPES:
        return

    ctx.template_vars["page_type_label"] = page_type_label_for(ctx.task.page_type)

    if ctx.use_serp:
        return

    site = ctx.db.query(Site).filter(Site.id == ctx.task.target_site_id).first()
    if not site:
        return

    template_id = None
    if ctx.task.project_id:
        from app.models.project import SiteProject

        project = ctx.db.query(SiteProject).filter(SiteProject.id == ctx.task.project_id).first()
        if project and isinstance(project.legal_template_map, dict):
            raw = project.legal_template_map.get(ctx.task.page_type)
            if raw is not None:
                template_id = str(raw)

    if not template_id and ctx.task.blueprint_page_id:
        bp_page = (
            ctx.db.query(BlueprintPage)
            .filter(BlueprintPage.id == ctx.task.blueprint_page_id)
            .first()
        )
        if bp_page and getattr(bp_page, "default_legal_template_id", None):
            template_id = str(bp_page.default_legal_template_id)

    lp = None
    if template_id:
        lp = (
            ctx.db.query(LegalPageTemplate)
            .filter(
                LegalPageTemplate.id == template_id,
                LegalPageTemplate.page_type == ctx.task.page_type,
                LegalPageTemplate.is_active == True,  # noqa: E712
            )
            .first()
        )

    if not lp:
        return

    legal_info = site.legal_info if isinstance(site.legal_info, dict) else {}
    content = substitute_legal_html(lp.content or "", legal_info)
    ctx.template_vars["legal_reference"] = content
    ctx.template_vars["legal_reference_html"] = content
    fmt = (lp.content_format or "text").lower()
    ctx.template_vars["legal_reference_format"] = fmt if fmt in ("text", "html") else "text"
    ctx.template_vars["legal_template_notes"] = lp.notes or ""

    merged: dict[str, Any] = {}
    if isinstance(lp.variables, dict):
        merged.update(lp.variables)
    merged.update(legal_info)
    ctx.template_vars["legal_variables"] = json.dumps(merged, ensure_ascii=False)
