# ТЗ: Экспорт проекта в DOCX + Additional Keywords с кластеризацией

---

## Контекст

Задача — изменить логику вкладки Project, чтобы контент-менеджер получал готовый файл для добавления на сайт. Две ключевые фичи:
1. Экспорт всех страниц проекта в один DOCX с мета-тегами и текстом
2. Additional Keywords на уровне проекта с автокластеризацией по страницам

---

## ЧАСТЬ 1: Экспорт проекта в DOCX

### 1.1. Общее описание

Новый endpoint `GET /projects/{id}/export-docx` генерирует один DOCX-файл со всеми завершёнными страницами проекта. Документ разбит на секции (page break между страницами). Для каждой страницы:
- Мета-теги (title, description)
- Контент (текст статьи)

### 1.2. Источник контента — универсальная логика

**Ключевой нюанс**: pipeline может генерировать как HTML, так и plain text (зависит от промптов пользователя). DOCX-экспорт должен работать в обоих случаях.

**Алгоритм выбора контента для каждой страницы:**

```
1. Берём article.html_content (результат после html_structure step)
2. Проверяем: содержит ли он HTML-теги (<h1>, <h2>, <p>, <ul>, <table>)?
   → ДА: режим HTML → конвертируем HTML → форматированный DOCX (заголовки, списки, параграфы)
   → НЕТ: режим Plain Text → вставляем как есть, разбивая по \n\n на параграфы
3. Fallback: если html_content пустой, берём step_results["final_editing"]["result"]
4. Fallback 2: если и он пустой — пропускаем страницу, логируем warning
```

### 1.3. Структура DOCX-документа

```
┌──────────────────────────────────────────────┐
│ ТИТУЛЬНАЯ СТРАНИЦА                           │
│                                              │
│ [Название проекта]                           │
│ Seed Keyword: [keyword]                      │
│ Сайт: [site_name / domain]                   │
│ Дата генерации: [date]                       │
│ Всего страниц: [N]                           │
│ Язык: [language] | Страна: [country]         │
├──────────────────── PAGE BREAK ──────────────┤
│ ОГЛАВЛЕНИЕ (Table of Contents)               │
│                                              │
│ 1. [page_title_1] (slug: /page-1) ......  3  │
│ 2. [page_title_2] (slug: /page-2) ......  7  │
│ ...                                          │
├──────────────────── PAGE BREAK ──────────────┤
│ СТРАНИЦА 1: [page_title]                     │
│                                              │
│ ┌─ Мета-теги ─────────────────────────────┐  │
│ │ Slug:        /page-slug                 │  │
│ │ Filename:    page-slug.html             │  │
│ │ Meta Title:  [из meta_generation]       │  │
│ │ Meta Desc:   [из meta_generation]       │  │
│ │ Keyword:     [main_keyword]             │  │
│ │ Word Count:  [N слов]                   │  │
│ └─────────────────────────────────────────┘  │
│                                              │
│ [Контент страницы — форматированный текст]   │
│ H1, H2, H3 → стили Heading в Word           │
│ <p> → параграфы                              │
│ <ul>/<ol> → нумерованные/маркированные       │
│ <table> → таблицы Word                       │
│ <a href="..."> → гиперссылки                 │
│ <strong>/<em> → bold/italic                  │
│                                              │
├──────────────────── PAGE BREAK ──────────────┤
│ СТРАНИЦА 2: [page_title]                     │
│ ... (аналогично)                             │
├──────────────────── PAGE BREAK ──────────────┤
│ ...                                          │
└──────────────────────────────────────────────┘
```

### 1.4. Конвертация HTML → DOCX элементы

Создать сервис `app/services/docx_builder.py` с функцией `build_project_docx(db, project_id) -> bytes`.

**HTML-парсинг через BeautifulSoup** (уже есть в зависимостях). Маппинг тегов:

| HTML тег          | DOCX элемент                                      |
| ----------------- | ------------------------------------------------- |
| `<h1>`            | Heading 1 (стиль Word)                            |
| `<h2>`            | Heading 2                                         |
| `<h3>`            | Heading 3                                         |
| `<h4>`            | Heading 4                                         |
| `<p>`             | Paragraph                                         |
| `<strong>`, `<b>` | Bold run                                          |
| `<em>`, `<i>`     | Italic run                                        |
| `<a href="...">`  | Hyperlink (текст ссылки + URL)                    |
| `<ul>` / `<li>`   | Bullet list                                       |
| `<ol>` / `<li>`   | Numbered list                                     |
| `<table>`         | Table                                             |
| `<br>`            | Line break внутри параграфа                       |
| `<img>`           | Пропускаем (или placeholder: "[Image: alt_text]") |
| Неизвестные теги  | Извлекаем текст, игнорируем тег                   |

**Библиотека**: `python-docx` (pip install python-docx). Это стандарт для серверной генерации DOCX в Python.

### 1.5. Таблица мета-тегов для каждой страницы

Перед контентом каждой страницы — стилизованная таблица:

```python
# Псевдокод для мета-блока
def add_meta_table(doc, page_data):
    """
    page_data = {
        "slug": "/best-casinos",
        "filename": "best-casinos.html", 
        "meta_title": "Best Online Casinos 2025",
        "meta_description": "Discover the top...",
        "main_keyword": "best online casinos",
        "word_count": 2450,
        "additional_keywords": ["casino bonus", "free spins", ...],  # из кластеризации
    }
    """
    table = doc.add_table(rows=7, cols=2)
    table.style = 'Light Shading Accent 1'
    
    rows_data = [
        ("Slug", page_data["slug"]),
        ("Filename", page_data["filename"]),
        ("Meta Title", page_data["meta_title"]),
        ("Meta Description", page_data["meta_description"]),
        ("Keyword", page_data["main_keyword"]),
        ("Additional Keywords", ", ".join(page_data.get("additional_keywords", []))),
        ("Word Count", str(page_data["word_count"])),
    ]
    
    for i, (label, value) in enumerate(rows_data):
        table.rows[i].cells[0].text = label  # bold
        table.rows[i].cells[1].text = value
```

### 1.6. Backend: Новый endpoint

**Файл: `app/api/projects.py`**

```python
@router.get("/{id}/export-docx")
def export_project_docx(id: str, db: Session = Depends(get_db)):
    """
    Генерирует DOCX со всеми завершёнными страницами проекта.
    Возвращает файл для скачивания.
    """
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Минимум одна завершённая задача
    completed_tasks = db.query(Task).filter(
        Task.project_id == id,
        Task.status == "completed"
    ).count()
    if completed_tasks == 0:
        raise HTTPException(status_code=400, detail="No completed pages to export")
    
    from app.services.docx_builder import build_project_docx
    
    docx_bytes = build_project_docx(db, str(project.id))
    
    safe_name = "".join(c for c in project.name if c.isalnum() or c in " -_")
    filename = f"{safe_name}.docx"
    
    return StreamingResponse(
        iter([docx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
```

### 1.7. Backend: Сервис docx_builder.py

**Новый файл: `app/services/docx_builder.py`**

Зависимости: `pip install python-docx beautifulsoup4`

```python
"""
Модуль генерации DOCX для проекта.
Один файл = все страницы проекта с мета-тегами и контентом.
"""
import io
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from bs4 import BeautifulSoup, Tag, NavigableString
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from sqlalchemy.orm import Session

from app.models.project import SiteProject
from app.models.task import Task
from app.models.article import GeneratedArticle
from app.models.blueprint import BlueprintPage


def build_project_docx(db: Session, project_id: str) -> bytes:
    """
    Основная функция. Собирает данные проекта, генерирует DOCX, возвращает bytes.
    
    Алгоритм:
    1. Загрузить project, tasks, articles, blueprint_pages
    2. Отсортировать по sort_order blueprint pages
    3. Для каждой завершённой страницы:
       a. Извлечь мета-теги из step_results["meta_generation"] или article.meta_data
       b. Извлечь контент из article.html_content (fallback: step_results["final_editing"])
       c. Определить режим: HTML или plain text
       d. Добавить в DOCX: мета-таблица + контент
    4. Сериализовать в bytes и вернуть
    """
    # ... реализация ...
    pass


def _is_html_content(text: str) -> bool:
    """
    Проверяет, содержит ли текст HTML-разметку.
    Ищет характерные теги: <h1>, <h2>, <p>, <ul>, <div>, <table>.
    """
    html_pattern = re.compile(r'<(h[1-6]|p|ul|ol|li|table|div|section|article)\b', re.IGNORECASE)
    return bool(html_pattern.search(text))


def _html_to_docx_elements(doc: Document, html: str):
    """
    Парсит HTML через BeautifulSoup и добавляет элементы в документ.
    
    Поддерживаемые теги: h1-h6, p, ul/ol/li, table/tr/td/th, 
    strong/b, em/i, a, br, img (как placeholder).
    
    Рекурсивно обходит дерево. Для inline-элементов (strong, em, a) 
    создаёт runs внутри текущего параграфа.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    for element in soup.children:
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                doc.add_paragraph(text)
        elif isinstance(element, Tag):
            _process_tag(doc, element)


def _process_tag(doc: Document, tag: Tag, current_paragraph=None):
    """
    Рекурсивный обработчик тегов.
    
    Блочные элементы (h1-h6, p, ul, ol, table) создают новые параграфы/элементы.
    Inline элементы (strong, em, a) добавляют runs в текущий параграф.
    """
    # ... детальная реализация маппинга тегов ...
    pass


def _add_plain_text_content(doc: Document, text: str):
    """
    Для plain-text контента: разбивает по двойным переносам на параграфы.
    Одинарные переносы → line break внутри параграфа.
    """
    paragraphs = text.split('\n\n')
    for para_text in paragraphs:
        para_text = para_text.strip()
        if para_text:
            p = doc.add_paragraph()
            lines = para_text.split('\n')
            for i, line in enumerate(lines):
                if i > 0:
                    p.add_run().add_break()
                p.add_run(line)


def _add_meta_table(doc: Document, page_data: dict):
    """
    Добавляет стилизованную таблицу с мета-информацией страницы.
    Серый фон для лейблов, белый для значений.
    """
    pass


def _get_meta_from_task(task: Task, article: Optional[GeneratedArticle]) -> dict:
    """
    Извлекает мета-теги из:
    1. article.meta_data (приоритет — JSON из meta_generation step)
    2. step_results["meta_generation"]["result"] (fallback — raw JSON string)
    3. article.title / article.description (fallback 2)
    
    Возвращает {"title": "...", "description": "...", ...}
    """
    pass


def _get_content_from_task(task: Task, article: Optional[GeneratedArticle]) -> Tuple[str, str]:
    """
    Извлекает контент и определяет его тип.
    
    Returns:
        (content_text, content_type)  где content_type = "html" | "plain"
    
    Приоритет:
    1. article.html_content → проверяем _is_html_content()
    2. step_results["final_editing"]["result"] → проверяем _is_html_content()
    3. "" (пустой — страница будет пропущена)
    """
    pass
```

**Важные детали реализации:**

1. **Очистка HTML перед конвертацией**: убрать `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>` теги — они из site template, а не из контента. Использовать `article.html_content` (контент без template), НЕ `article.full_page_html` (с template).

2. **Обработка изображений**: если в HTML есть `<img>`, вставляем текстовый placeholder `[Image: {alt_text}]` курсивом. Скачивание и вставка реальных картинок — опционально, за рамками MVP.

3. **Длинные мета-описания**: в таблице мета-тегов ячейка `Meta Description` может быть длинной — убедиться что ширина колонки достаточна (70% ширины страницы).

### 1.8. Frontend: Кнопка экспорта

**Файл: `frontend/src/pages/ProjectDetailPage.tsx`**

Добавить кнопку рядом с существующими "Export Summary (CSV)" и "Download ZIP":

```tsx
{/* Показывать когда есть хотя бы 1 completed task */}
{(project.completed_tasks ?? 0) > 0 && (
  <a
    href={`${API_URL}/projects/${id}/export-docx`}
    download
    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium shadow-sm transition-colors"
  >
    <FileText className="w-4 h-4" /> Export DOCX
  </a>
)}
```

**Файл: `frontend/src/api/projects.ts`**

Добавить метод (опционально, если нужна программная загрузка):

```typescript
exportDocx: (id: string) => {
    window.open(`${API_URL}/projects/${id}/export-docx`, '_blank');
},
```

### 1.9. Зависимости

**Backend:**
```
pip install python-docx --break-system-packages
```

`python-docx` уже зрелая библиотека, 0 внешних зависимостей кроме lxml (который уже есть).

---

## ЧАСТЬ 2: Additional Keywords на уровне проекта + кластеризация

### 2.1. Общее описание

Пользователь при создании проекта добавляет список дополнительных ключевых слов (до 100 штук). Система через LLM-вызов кластеризует их по страницам blueprint. Пользователь видит preview распределения и может скорректировать. При генерации — ключи передаются в `additional_keywords` каждого таска.

### 2.2. Модель данных

**Файл: `app/models/project.py`** — добавить поле в `SiteProject`:

```python
class SiteProject(Base):
    __tablename__ = "site_projects"
    
    # ... существующие поля ...
    
    # НОВОЕ ПОЛЕ
    project_keywords = Column(
        JSONB, 
        nullable=True, 
        default=dict,
        comment="Additional keywords pool + clustering result. Format: {raw: [...], clustered: {page_slug: [...]}}"
    )
```

**Структура JSON `project_keywords`:**

```json
{
  "raw": [
    "casino bonus codes",
    "free spins no deposit",
    "best slot machines",
    "...до 100 штук"
  ],
  "clustered": {
    "page_slug_1": {
      "page_title": "Best Online Casinos",
      "keyword": "best online casinos",
      "assigned_keywords": ["casino bonus codes", "top rated casinos", "casino reviews"]
    },
    "page_slug_2": {
      "page_title": "Free Spins Guide", 
      "keyword": "free spins",
      "assigned_keywords": ["free spins no deposit", "free spins bonus"]
    }
  },
  "unassigned": ["keyword that didn't fit anywhere"],
  "clustering_model": "openai/gpt-4o",
  "clustering_cost": 0.0023
}
```

**Миграция Alembic:**

```python
"""add project_keywords to site_projects"""

def upgrade():
    op.add_column('site_projects', 
        sa.Column('project_keywords', JSONB, nullable=True, server_default='{}')
    )

def downgrade():
    op.drop_column('site_projects', 'project_keywords')
```

### 2.3. API: Кластеризация ключевых слов

**Файл: `app/api/projects.py`** — новый endpoint:

```python
class ClusterKeywordsRequest(BaseModel):
    keywords: List[str]  # raw list, до 100 штук
    blueprint_id: str

class ClusterKeywordsResponse(BaseModel):
    clustered: Dict[str, dict]  # page_slug → {page_title, keyword, assigned_keywords}
    unassigned: List[str]
    total_keywords: int
    total_assigned: int
    cost: float


@router.post("/cluster-keywords")
def cluster_project_keywords(
    body: ClusterKeywordsRequest, 
    db: Session = Depends(get_db)
):
    """
    Принимает список ключевых слов + blueprint_id.
    Через LLM кластеризует ключи по страницам blueprint.
    Возвращает preview распределения (без сохранения — пользователь должен подтвердить).
    """
    if len(body.keywords) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 keywords allowed")
    if len(body.keywords) == 0:
        raise HTTPException(status_code=400, detail="At least 1 keyword required")
    
    # Загрузить страницы blueprint
    blueprint = db.query(SiteBlueprint).filter(SiteBlueprint.id == body.blueprint_id).first()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    
    pages = db.query(BlueprintPage).filter(
        BlueprintPage.blueprint_id == body.blueprint_id
    ).order_by(BlueprintPage.sort_order).all()
    
    if not pages:
        raise HTTPException(status_code=400, detail="Blueprint has no pages")
    
    from app.services.keyword_clusterer import cluster_keywords
    
    result = cluster_keywords(
        keywords=body.keywords,
        pages=[{
            "slug": p.page_slug,
            "title": p.page_title,
            "keyword_template": p.keyword_template,
            "page_type": p.page_type,
        } for p in pages]
    )
    
    return result
```

### 2.4. Сервис кластеризации

**Новый файл: `app/services/keyword_clusterer.py`**

```python
"""
Кластеризация дополнительных ключевых слов по страницам blueprint через LLM.

Подход: один LLM-вызов с JSON response_format.
Для ≤100 keywords и ≤30 pages — укладывается в один запрос GPT-4o.
"""
import json
from typing import List, Dict, Any

from app.services.llm import generate_text
from app.config import settings


def cluster_keywords(
    keywords: List[str],
    pages: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Кластеризует keywords по pages через LLM.
    
    Args:
        keywords: список ключевых слов (до 100)
        pages: список страниц [{slug, title, keyword_template, page_type}]
    
    Returns:
        {
            "clustered": {page_slug: {page_title, keyword, assigned_keywords: [...]}},
            "unassigned": [...],
            "total_keywords": N,
            "total_assigned": N,
            "cost": float
        }
    """
    
    # Формируем описание страниц для LLM
    pages_description = "\n".join([
        f"- slug: \"{p['slug']}\" | title: \"{p['title']}\" | keyword: \"{p['keyword_template']}\" | type: {p['page_type']}"
        for p in pages
    ])
    
    keywords_list = "\n".join([f"- {kw}" for kw in keywords])
    
    system_prompt = """You are an SEO keyword clustering expert. 
Your task is to assign additional keywords to the most relevant pages of a website.

Rules:
1. Each keyword should be assigned to exactly ONE page (the most relevant one)
2. A keyword can be left unassigned if no page is a good fit
3. Consider semantic relevance, search intent, and topical proximity
4. A page can have 0 to many keywords assigned
5. Respond ONLY with valid JSON, no markdown wrapping"""

    user_prompt = f"""Website pages:
{pages_description}

Additional keywords to distribute:
{keywords_list}

Assign each keyword to the most relevant page. Respond with this exact JSON structure:
{{
  "assignments": {{
    "page_slug_1": ["keyword1", "keyword2"],
    "page_slug_2": ["keyword3"]
  }},
  "unassigned": ["keyword that doesn't fit any page"]
}}

Use exact page slugs and exact keywords from the lists above. Every keyword must appear exactly once — either in assignments or in unassigned."""

    # Определяем модель для кластеризации
    model = getattr(settings, "CLUSTERING_MODEL", "openai/gpt-4o")
    
    response, cost, actual_model = generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        max_tokens=4000,
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    # Парсим результат
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        # Fallback: попробовать очистить от markdown
        cleaned = response.strip().strip('`').strip()
        if cleaned.startswith('json'):
            cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
    
    assignments = parsed.get("assignments", {})
    unassigned = parsed.get("unassigned", [])
    
    # Формируем enriched result с информацией о страницах
    pages_by_slug = {p["slug"]: p for p in pages}
    clustered = {}
    total_assigned = 0
    
    for slug, assigned_kws in assignments.items():
        page_info = pages_by_slug.get(slug, {})
        clustered[slug] = {
            "page_title": page_info.get("title", slug),
            "keyword": page_info.get("keyword_template", ""),
            "assigned_keywords": assigned_kws
        }
        total_assigned += len(assigned_kws)
    
    # Добавить страницы без ключей (для полноты картины)
    for p in pages:
        if p["slug"] not in clustered:
            clustered[p["slug"]] = {
                "page_title": p["title"],
                "keyword": p["keyword_template"],
                "assigned_keywords": []
            }
    
    return {
        "clustered": clustered,
        "unassigned": unassigned,
        "total_keywords": len(keywords),
        "total_assigned": total_assigned,
        "cost": cost,
        "model": actual_model,
    }
```

### 2.5. Интеграция в генерацию страниц

**Файл: `app/workers/tasks.py`** — в функции `process_project_page`:

При создании Task для страницы проекта, нужно подставить additional_keywords из кластеризации:

```python
# В process_project_page, при создании/обновлении project_task:

# Получить clustered keywords для этой страницы
clustered_kws = []
project_kws = getattr(project, "project_keywords", None) or {}
clustered_data = project_kws.get("clustered", {})
page_cluster = clustered_data.get(page.page_slug, {})
clustered_kws = page_cluster.get("assigned_keywords", [])

# Объединить с существующими additional_keywords (если есть)
existing_kws = project_task.additional_keywords or ""
if clustered_kws:
    clustered_str = ", ".join(clustered_kws)
    if existing_kws:
        project_task.additional_keywords = f"{existing_kws}, {clustered_str}"
    else:
        project_task.additional_keywords = clustered_str
```

**Файл: `app/services/pipeline.py`** — в `setup_template_vars`:

Никаких изменений не нужно! `additional_keywords` уже читается из `ctx.task.additional_keywords` и передаётся как `{{additional_keywords}}` в промпты. Кластеризованные ключи подставятся автоматически.

### 2.6. Frontend: UI для ввода keywords + preview кластеризации

**Файл: `frontend/src/pages/ProjectsPage.tsx`** — в форме создания проекта:

#### 2.6.1. Новое поле ввода

Добавить после поля Seed Keyword:

```tsx
<div>
  <label className="block text-sm font-medium text-slate-700 mb-1">
    Additional Keywords (optional, max 100)
  </label>
  <textarea
    rows={4}
    placeholder="Enter keywords, one per line or comma-separated&#10;casino bonus codes&#10;free spins no deposit&#10;best slot machines"
    value={formData.additional_keywords_raw}
    onChange={(e) => setFormData({ ...formData, additional_keywords_raw: e.target.value })}
    className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
  />
  <p className="text-xs text-slate-400 mt-1">
    {parseKeywords(formData.additional_keywords_raw).length} / 100 keywords
  </p>
</div>
```

#### 2.6.2. Парсинг ввода

```typescript
function parseKeywords(raw: string): string[] {
  if (!raw.trim()) return [];
  
  // Поддержка: одно на строку ИЛИ через запятую
  return raw
    .split(/[\n,]/)
    .map(kw => kw.trim())
    .filter(kw => kw.length > 0)
    .slice(0, 100);
}
```

#### 2.6.3. Кнопка "Cluster Keywords" + Preview

Добавить кнопку в форме, которая вызывает `/projects/cluster-keywords` и показывает preview:

```tsx
{parsedKeywords.length > 0 && formData.blueprint_id && (
  <button
    type="button"
    onClick={() => clusterMutation.mutate({
      keywords: parsedKeywords,
      blueprint_id: formData.blueprint_id
    })}
    disabled={clusterMutation.isPending}
    className="flex items-center gap-2 px-4 py-2 border border-slate-300 bg-white text-slate-800 rounded-lg text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
  >
    <Shuffle className="w-4 h-4" />
    {clusterMutation.isPending ? "Clustering..." : "Cluster Keywords"}
  </button>
)}
```

#### 2.6.4. Preview результата кластеризации

```tsx
{clusterResult && (
  <div className="border rounded-lg p-4 bg-slate-50 space-y-3">
    <div className="flex justify-between items-center">
      <h4 className="font-semibold text-sm text-slate-800">
        Keyword Distribution Preview
      </h4>
      <span className="text-xs text-slate-500">
        {clusterResult.total_assigned}/{clusterResult.total_keywords} assigned
        | Cost: ${clusterResult.cost.toFixed(4)}
      </span>
    </div>
    
    {Object.entries(clusterResult.clustered).map(([slug, data]) => (
      <div key={slug} className="bg-white rounded border p-3">
        <div className="flex justify-between">
          <span className="font-medium text-sm">{data.page_title}</span>
          <span className="text-xs text-slate-400">{data.assigned_keywords.length} keywords</span>
        </div>
        <p className="text-xs text-slate-500 mt-1">Main: {data.keyword}</p>
        {data.assigned_keywords.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {data.assigned_keywords.map((kw, i) => (
              <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>
    ))}
    
    {clusterResult.unassigned.length > 0 && (
      <div className="bg-amber-50 rounded border border-amber-200 p-3">
        <span className="font-medium text-sm text-amber-800">Unassigned ({clusterResult.unassigned.length})</span>
        <div className="flex flex-wrap gap-1 mt-2">
          {clusterResult.unassigned.map((kw, i) => (
            <span key={i} className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">
              {kw}
            </span>
          ))}
        </div>
      </div>
    )}
  </div>
)}
```

#### 2.6.5. Сохранение при создании проекта

При отправке формы создания проекта, если есть результат кластеризации — передавать его:

**Файл: `app/api/projects.py`** — обновить `SiteProjectCreate`:

```python
class SiteProjectCreate(BaseModel):
    name: str
    blueprint_id: str
    target_site: str
    seed_keyword: str
    seed_is_brand: bool = False
    country: str
    language: str
    author_id: Optional[int] = None
    serp_config: Optional[Dict[str, Any]] = None
    # НОВОЕ ПОЛЕ
    project_keywords: Optional[Dict[str, Any]] = None  # {raw: [...], clustered: {...}}
```

В `create_project()`:

```python
# После создания объекта new_project:
if project_in.project_keywords:
    new_project.project_keywords = project_in.project_keywords
```

**Файл: `frontend/src/api/projects.ts`** — обновить `SiteProjectCreatePayload`:

```typescript
export interface SiteProjectCreatePayload {
  // ... существующие поля ...
  project_keywords?: {
    raw: string[];
    clustered: Record<string, {
      page_title: string;
      keyword: string;
      assigned_keywords: string[];
    }>;
    unassigned: string[];
    clustering_model: string;
    clustering_cost: number;
  };
}
```

### 2.7. Конфигурация

**Файл: `app/config.py`** — добавить:

```python
# Keyword Clustering
CLUSTERING_MODEL: str = "openai/gpt-4o"  # модель для кластеризации keywords
MAX_PROJECT_KEYWORDS: int = 100  # максимум доп. ключей на проект
```

---

## ЧАСТЬ 3: Интеграция — Additional Keywords в DOCX

В DOCX-экспорте (часть 1), для каждой страницы в мета-таблицу добавляется строка "Additional Keywords" со значением из `project_keywords.clustered[slug].assigned_keywords`.

Это уже предусмотрено в структуре мета-таблицы (пункт 1.5):

```python
("Additional Keywords", ", ".join(page_data.get("additional_keywords", []))),
```

Данные берутся из `project.project_keywords["clustered"][page_slug]["assigned_keywords"]`.

---

## Порядок реализации

### Этап 1: Модель + миграция (15 мин)
1. Добавить поле `project_keywords` в `SiteProject` модель
2. Создать и применить Alembic миграцию

### Этап 2: Кластеризация keywords (2-3 часа)
1. Создать `app/services/keyword_clusterer.py`
2. Добавить endpoint `POST /projects/cluster-keywords`
3. Обновить `SiteProjectCreate` schema
4. Обновить `create_project()` — сохранение project_keywords
5. Обновить `process_project_page()` — подстановка keywords в Task

### Этап 3: Frontend для keywords (2-3 часа)  
1. Добавить textarea для keywords в форму создания проекта
2. Кнопка "Cluster Keywords" + вызов API
3. Preview компонент с результатами кластеризации
4. Передача project_keywords при создании проекта

### Этап 4: DOCX экспорт (3-4 часа)
1. `pip install python-docx`
2. Создать `app/services/docx_builder.py` с полной логикой
3. Добавить endpoint `GET /projects/{id}/export-docx`
4. Кнопка "Export DOCX" на ProjectDetailPage

### Этап 5: Тестирование (1-2 часа)
1. Создать проект с 3-5 страницами и 20-30 keywords
2. Проверить кластеризацию: preview → создание → генерация
3. Проверить DOCX: скачать, открыть в Word/Google Docs, проверить форматирование
4. Проверить edge case: проект без keywords, проект с plain text вместо HTML

---

## Edge Cases

1. **Страница без article** (failed/stale task) → пропускается в DOCX, в оглавлении помечается как "[не сгенерирована]"
2. **Пустой meta_generation** → используем article.title / article.description как fallback
3. **HTML с broken тегами** → BeautifulSoup автоматически исправит (`html.parser`)
4. **Keyword уже есть в additional_keywords таска** → дедупликация при объединении (set)
5. **Blueprint изменился после кластеризации** → preview показывает текущее состояние, при пересоздании нужно перекластеризовать
6. **0 keywords введено** → кнопка "Cluster" скрыта, project_keywords = null
7. **Все keywords попали в unassigned** → предупреждение в UI: "Keywords don't match any page well"
