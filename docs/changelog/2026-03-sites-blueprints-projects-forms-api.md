# Март 2026 — Sites, Blueprints, Projects (формы и API)

**Дата:** 2026-03-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Sites (`SitesPage.tsx`, `app/api/sites.py`):**
- Модалка **Add Site**: поля **Country** и **Language** — `<select>` со списками из уникальных значений **`GET /api/authors`** (как в `TasksPage`), дефолт пустой, placeholder-опции «Select country...» / «Select language...».
- **`DELETE /api/sites/{site_id}`:** если у сайта есть связанные **задачи** (`Task.target_site_id`) или **проекты** (`SiteProject.site_id`), ответ **409** с текстом вида `Cannot delete: site has N tasks and M projects. Delete them first.`; иначе удаляется запись **Site** (глобальные **`templates`** не удаляются). При ошибке удаления в UI в toast показывается **`detail`** из тела ответа API.

**Blueprints (`BlueprintsPage.tsx`, `app/api/blueprints.py`):**
- Таблица блупринтов с **раскрывающейся строкой**; под ней панель **Pages** (lazy `useQuery` → `GET /api/blueprints/{id}/pages`), таблица страниц, **Add Page** / редактирование / удаление, блок **Keyword Preview** (клиентская подстановка `{seed}`).
- После успешного **Create Blueprint** автоматически раскрывается только что созданный блупринт (`setExpandedBlueprintId` по `id` из ответа `POST /api/blueprints`).
- Управление страницами: в т.ч. `DELETE /api/blueprints/{id}/pages/{page_id}` (ответ `{"status": "deleted"}`).

**Projects (`ProjectsPage.tsx`):**
- Модалка **New Project**: **Country** / **Language** — `<select>` из уникальных значений авторов (списки дополняются значениями выбранного **Target Site** и текущего формы, чтобы GEO из сайта всегда было в опциях).
- **Author** — `<select>` авторов, отфильтрованных по выбранным country + language; первая опция **Auto (by country/language)** (`""`); при незаполненном GEO селект задизейблен с единственной опцией **Auto**; при смене country/language сбрасывается `author_id`.
- При выборе **Target Site** предзаполняются **country** и **language** из объекта сайта в кэше `sites`.
