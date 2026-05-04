# 30 марта 2026 — Проекты: архивация, устойчивость к сбоям SERP, расширение API и UI

**Дата:** 2026-03-30
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Модель и миграция**
- **`SiteProject.is_archived`** (Boolean, default false). Миграция: **`alembic/versions/e7f8a9b0c1d2_add_is_archived_to_site_projects.py`**.

**API (`app/api/projects.py`)**
- **`GET /api/projects`**: query **`archived`** (по умолчанию только неархивные), **`status`**, **`search`** (имя, `ilike`); в каждом элементе: **`is_archived`**, **`country`**, **`language`**, **`total_tasks`**, **`completed_tasks`**, **`failed_tasks`**, **`progress`**.
- **`GET /api/projects/{id}`**: **`failed_count`**, **`is_archived`**, **`progress`**, **`error_log`**.
- **`POST /api/projects/{id}/archive`**, **`POST /api/projects/{id}/unarchive`** — без ограничения по статусу проекта.
- **`DELETE /api/projects/{id}`** — удаление проекта и связанных **Task**; запрещено при статусе **`generating`** или **`pending`**.
- **`POST /api/projects/{id}/retry-failed`** — задачи со статусом **`failed`** → **`pending`**, повторная постановка **`process_site_project`** в очередь.

**Pipeline (`app/services/pipeline.py`)**
- **`phase_serp`**: вызов **`fetch_serp_data`** в **try/except**; при ошибке — лог, **`save_step_result`** для **`serp_research`** со **`status="failed"`**, **`raise`** (задача завершается как failed).

**Worker (`app/workers/tasks.py`, `process_site_project`)**
- Ошибка страницы не переводит весь проект в **`failed`**: накопление **`failed_pages`**, **`continue`** к следующей странице; после обхода всех страниц — **`build_site`**, **`project.status = "completed"`**, **`error_log`** = JSON массива сбоев или **`None`**; при **Stop** сохраняется накопленный **`error_log`**.

**React**
- **`frontend/src/pages/ProjectsPage.tsx`**: переключатель **Active / Archived**, фильтр статуса, поиск по имени; колонки **Country/Lang**, **Pages**, **Failed**; иконки **Archive** / **ArchiveRestore**.
- **`frontend/src/pages/ProjectDetailPage.tsx`**: **Retry Failed Pages**, **Delete** (confirm), счётчик failed, блоки ошибок (красный для **`failed`**, янтарный для **`completed`** + **`error_log`** — частичные сбои страниц).
- **`frontend/src/api/projects.ts`**: **`archiveProject`**, **`unarchiveProject`**, **`deleteProject`**, **`retryFailedPages`**, расширенный **`getAll`**.

---
