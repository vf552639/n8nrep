import random
from typing import Optional
from sqlalchemy.orm import Session
from app.models.site import SiteTemplate, Site
import datetime

def generate_full_page(db: Session, site_id: str, html_content: str, title: str, description: str) -> Optional[str]:
    """
    Picks a random active template for the given site_id (preferring those with minimum usage_count).
    Injects the generated content, title, and description into the template.
    Returns the full HTML page or None if no template found.
    """
    # Get all active templates for this site
    templates = db.query(SiteTemplate).filter(
        SiteTemplate.site_id == site_id,
        SiteTemplate.is_active == True
    ).all()
    
    if not templates:
        return None
        
    # Find template(s) with minimum usage_count
    min_usage = min(t.usage_count for t in templates)
    candidate_templates = [t for t in templates if t.usage_count == min_usage]
    
    # Pick a random one from the candidates
    selected_template = random.choice(candidate_templates)
    
    # Simple placeholder injection (can be expanded to use Jinja2 later if needed)
    full_html = selected_template.html_template
    
    # Common placeholders that might be in the template
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
        "{year}": str(datetime.datetime.now().year)
    }
    
    for placeholder, new_val in replacements.items():
        if placeholder in full_html:
            full_html = full_html.replace(placeholder, new_val)
            
    # Also attempt standard HTML `<title>` replacement if placeholders weren't explicitly used
    if "<title>" in full_html and "</title>" in full_html and "{" not in full_html.split("<title>")[1].split("</title>")[0]:
        import re
        full_html = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', full_html, flags=re.IGNORECASE)
        
    if '<meta name="description"' in full_html:
        import re
        full_html = re.sub(
            r'<meta\s+name=["\']description["\']\s+content=["\'].*?["\']\s*/?>',
            f'<meta name="description" content="{description}">',
            full_html,
            flags=re.IGNORECASE
        )
    
    # Increment usage count
    selected_template.usage_count += 1
    db.commit()
    
    return full_html

def get_template_for_reference(db: Session, site_id: str) -> tuple:
    """
    Returns HTML template of the site to be used as a reference in LLM prompts.
    Does NOT increment usage_count.
    Picks the active template with minimum usage_count deterministically.
    Returns:
        tuple: (html_template: str | None, template_name: str | None)
    """
    templates = db.query(SiteTemplate).filter(
        SiteTemplate.site_id == site_id,
        SiteTemplate.is_active == True
    ).all()
    
    if not templates:
        return (None, None)
        
    min_usage = min(t.usage_count for t in templates)
    candidate_templates = [t for t in templates if t.usage_count == min_usage]
    
    selected = candidate_templates[0]
    return (selected.html_template, selected.template_name)
