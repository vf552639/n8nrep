# 18 апреля 2026 — Проект: `use_site_template` (обёртка сайта опционально)

**Дата:** 2026-04-18
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Цель:** шаблон HTML остаётся привязанным к **`Site.template_id`**, но для конкретного **`SiteProject`** можно отключить использование обёртки: статьи — «сырой» HTML без head/CSS/header/footer; **`sites.template_id`** не меняется (другие проекты того же сайта могут оставаться с обёрткой).

**База данных и модель**
- Таблица **`site_projects`**: колонка **`use_site_template`** (**`BOOLEAN NOT NULL`**, **`DEFAULT TRUE`**).
- Миграция **`r4s5t6u7v8wd_add_use_site_template_to_site_projects`** (`down_revision`: **`q3r4s5t6u7vc`**).
- Модель **`app/models/project.py`** — поле **`SiteProject.use_site_template`**.

**Backend — `app/api/projects.py`**
- **`SiteProjectCreate`**, **`ProjectPreviewRequest`**: **`use_site_template: bool = True`**.
- **`SiteProjectCloneBody`**: опциональный **`use_site_template`**; при отсутствии в теле — копируется с исходного проекта.
- **`POST /api/projects`**, **`GET /api/projects`**, **`GET /api/projects/{id}`** — сохранение и отдача флага.
- **`POST /api/projects/preview`**: эффективный **`has_template`** = наличие активного шаблона у сайта **и** **`use_site_template`**; при **`use_site_template=False`** при активном шаблоне сайта — **`warnings`**: *"Site template disabled for this project. Articles will be raw HTML."*; в **`site`** добавлено **`use_site_template`** (эхо запроса).
- **`POST /api/projects/{id}/clone`** — запись **`use_site_template`** в новую строку.

**Backend — пайплайн и сборка страницы**
- **`app/services/pipeline.py` — `setup_template_vars`**: если у задачи есть **`project_id`** и у проекта **`use_site_template`** ложь — **`site_template_html`** / **`site_template_name`** принудительно пустые (нет **`[SITE TEMPLATE REFERENCE]`** в **`html_structure`**, **`programmatic_html_insert`** получает пустой шаблон → возвращает тело статьи).
- **`app/services/template_engine.py` — `generate_full_page`**: аргумент **`project_id: Optional[str]`**; при отключённом флаге у проекта — **`return None`** → **`GeneratedArticle.full_page_html`** может быть **`NULL`**, контент в **`html_content`**.

**Backend — ZIP**
- **`app/services/site_builder.py`**: для файла в архиве используется **`full_page_html`**, при его отсутствии — **`html_content`**, чтобы проекты без обёртки не давали пустой ZIP.

**Frontend**
- **`SiteProjectCreatePayload`**, типы **`Project`**, **`ProjectPreview.site`**, **`ProjectClonePayload`**: поле **`use_site_template`**.
- **`ProjectsPage.tsx`** (модалка **New Project**): чекбокс *Use site HTML template* только если у выбранного сайта есть **`template_id`**; preview/create передают флаг; бейдж **Template: OFF** в превью при **`use_site_template === false`**.
- **`ProjectDetailPage.tsx`** (**Clone project**): тот же чекбокс и передача в **`cloneProject`**.

---
