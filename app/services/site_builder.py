import os
import zipfile
import tempfile
from sqlalchemy.orm import Session

from app.models.project import SiteProject
from app.models.task import Task
from app.models.article import GeneratedArticle
from app.models.blueprint import BlueprintPage

def build_site(db: Session, project_id: str) -> str:
    """
    Builds the final website for a project by injecting navigation 
    and compressing all pages into a ZIP archive.
    Returns the path to the created ZIP file.
    """
    project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
    if not project:
        raise Exception(f"Project {project_id} not found")

    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    task_ids = [t.id for t in tasks]
    
    articles = db.query(GeneratedArticle).filter(GeneratedArticle.task_id.in_(task_ids)).all()
    article_by_task = {a.task_id: a for a in articles}
    
    # We need blueprint pages to know filenames and navigation labels
    pages = db.query(BlueprintPage).filter(BlueprintPage.blueprint_id == project.blueprint_id).order_by(BlueprintPage.sort_order).all()
    
    # Build navigation HTML
    nav_links = []
    footer_links = []
    
    for p in pages:
        if p.show_in_nav:
            label = p.nav_label or p.page_title
            nav_links.append(f'<li><a href="{p.filename}">{label}</a></li>')
        if p.show_in_footer:
            label = p.nav_label or p.page_title
            footer_links.append(f'<li><a href="{p.filename}">{label}</a></li>')
            
    header_nav = f"<ul>{''.join(nav_links)}</ul>" if nav_links else ""
    footer_nav = f"<ul>{''.join(footer_links)}</ul>" if footer_links else ""
    
    # Create temp directory
    tmp_dir = tempfile.mkdtemp(prefix=f"site_{project_id}_")
    
    for task in tasks:
        if not task.blueprint_page_id:
            continue
            
        page = next((p for p in pages if str(p.id) == str(task.blueprint_page_id)), None)
        if not page:
            continue
            
        article = article_by_task.get(task.id)
        if not article or not article.full_page_html:
            print(f"Warning: No generated article found for task {task.id}")
            continue
            
        html_content = article.full_page_html
        
        # Inject navigation
        html_content = html_content.replace("<!-- NAV -->", header_nav)
        html_content = html_content.replace("<!-- FOOTER_NAV -->", footer_nav)
        
        file_path = os.path.join(tmp_dir, page.filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    
    # Ensure export directory exists
    export_dir = os.path.join(os.getcwd(), "data", "exports")
    os.makedirs(export_dir, exist_ok=True)
    
    zip_filename = f"project_{project.id}.zip"
    zip_path = os.path.join(export_dir, zip_filename)
    
    # Create ZIP archive
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = file
                zipf.write(file_path, arcname)
                
    # Cleanup temp dir (optional, can leave for debugging but good practice)
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
                
    project.build_zip_url = zip_path
    db.commit()
    
    return zip_path
