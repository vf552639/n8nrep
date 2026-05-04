# 1 апреля 2026 — Templates, Legal Pages, связь Site → Template

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Модели и БД**
- Таблица **`templates`**: переиспользуемые HTML-оболочки (name, html_template, description, preview_screenshot, is_active, timestamps). Таблица **`site_templates`** удалена; миграция **`i3d4e5f6a7b8`** переносит данные и проставляет **`sites.template_id`**.
- Таблица **`legal_page_templates`**: country, page_type (privacy_policy, terms_and_conditions, cookie_policy, responsible_gambling, about_us), title, html_content, variables (JSONB), notes, is_active; **UNIQUE(country, page_type)**.
- **`sites`**: **`template_id`** (FK → templates), **`legal_info`** (JSONB) — company_name, contact_email, address и т.д. для legal-страниц.

**Backend**
- **`app/api/templates.py`** — `GET/POST/PUT/DELETE /api/templates`; удаление шаблона запрещено, если на него ссылаются сайты (**409**).
- **`app/api/legal_pages.py`** — CRUD `/api/legal-pages`, метаданные **`GET /api/legal-pages/meta/page-types`** (статический путь до `/{id}`).
- **`app/api/sites.py`** — без вложенных `/sites/{id}/templates`; **`GET/PATCH /api/sites/{id}`**, в списке **`template_name`**.
- **`app/services/template_engine.py`** — шаблон по **`Site.template_id`**; **`get_template_for_reference`** возвращает HTML и **name** из **`Template`**.
- **`app/services/legal_reference.py`** — в **`inject_legal_template_vars`** / **`setup_template_vars`**: при **use_serp=false** и **`page_type`** из legal-набора подставляются образец (**`legal_reference`** / **`legal_reference_html`** — один текст, плейсхолдеры `{{...}}` из **`legal_info`**), **`legal_variables`** (JSON). Расширение (**`legal_reference_format`**, **`legal_template_notes`**, **`page_type_label`**) — см. раздел **«21 апреля 2026»** выше.

**Frontend**
- **`/templates`** — `TemplatesPage`: список шаблонов (в т.ч. **sites_count**), модалка name / description / HTML (Monaco).
- **`/sites`** — `SitesPage`: сайты, колонка Template; создание с выбором **`template_id`**.
- **`/sites/:id`** — `SiteDetailPage`: выбор шаблона, редактор **`legal_info`** (JSON).
- **`/legal-pages`** — `LegalPagesPage`: таблица + фильтр country, модалка с типами страниц и Variables JSON.
- Sidebar: **Templates**, **Sites**, **Legal Pages** — отдельные пункты.

**Промпты:** в списках переменных — legal: **`legal_reference`**, **`legal_reference_html`**, **`legal_variables`** и далее по **`PromptsPage.tsx`** (актуализация **21.04.2026**).

**Превью проекта:** проверка наличия HTML-шаблона у сайта — через **`site.template_id`** и активный **`Template`** (не **`SiteTemplate`**).

---
