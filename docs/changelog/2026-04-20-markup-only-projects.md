# 20 апреля 2026 — Markup only: создание проекта без Target Site

**Дата:** 2026-04-20
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** нужна генерация «только разметка» (content-only) без привязки к реальному сайту и без HTML-обёртки (head / header / footer). Колонка **`site_projects.site_id`** остаётся **NOT NULL** — миграции БД не требуются.

**Backend — `app/api/projects.py`**
- Константа **`MARKUP_ONLY_SITE_KEY = "__markup_only__"`** и **`_resolve_site_or_markup_only(db, target_site, country, language, use_site_template)`**: при непустом **`target_site`** — обычный **`_resolve_site`** и переданный флаг обёртки; при **`None`** / пустой строке (после нормализации валидатором) — **`_resolve_site(db, MARKUP_ONLY_SITE_KEY, …)`** (создание или переиспользование placeholder-строки в **`sites`**) и **`use_site_template=False`**.
- **`SiteProjectCreate.target_site`**, **`ProjectPreviewRequest.target_site`** — **`Optional[str] = None`**; **`field_validator`** приводит пустую строку к **`None`**.
- **`create_project`**: резолв сайта и флага через **`_resolve_site_or_markup_only`**; в **`SiteProject`** пишется **`use_site_template`** с учётом результата helper.
- **`preview_project`**: без **`target_site`** — readonly по **`MARKUP_ONLY_SITE_KEY`**, **`effective_use_site_template = False`**, предупреждение в **`warnings`** про markup-only; в ответе **`site.use_site_template`** и **`has_template`** согласованы с этим режимом.
- **`clone_project`**: если в теле передан **`target_site`** (не **`None`** после strip) — **`_resolve_site_or_markup_only`**; если поле опущено — по-прежнему сайт исходного проекта и логика **`use_site_template`** из тела/источника.
- **`SiteProjectCloneBody`**: нормализация **`target_site`** (пустая строка → **`None`**, наследование сайта при clone).

**Frontend**
- **`frontend/src/api/projects.ts`**: **`SiteProjectCreatePayload.target_site?: string`**.
- **`frontend/src/pages/ProjectsPage.tsx`** (модалка **Create Generative Project**): состояние **`markup_only`**; чекбокс **Markup only**; при включении — **`site_id: ""`**, **`use_site_template: false`**, скрыты блоки **Target Site** и **Use site HTML template**; **Preview** / **Start** без сайта; в API не отправляется **`target_site`**, **`use_site_template: false`**; валидация и подсказка у **Author** учитывают режим.

---
