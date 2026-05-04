# 19 апреля 2026 — Зависшие проекты: force-delete, массовое удаление, reset-status, каскад сайта

**Дата:** 2026-04-19
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** если Celery падает без обработки, проект мог оставаться в **`pending`**/**`generating`** и не удалялся обычным **`DELETE`**. Нужны явные операции восстановления и каскадное удаление сайта с проектами.

**Backend — `app/api/projects.py`**
- **`DELETE /{id}?force=false|true`**: при **`force=False`** — по-прежнему **400**, если статус **`pending`** или **`generating`**. При **`force=True`** — **`_revoke_project_celery_task(project.celery_task_id)`** ( **`celery_app.control.revoke(..., terminate=True)`** ), затем удаление всех **`Task`** с **`project_id`**, удаление **`SiteProject`**.
- **`POST /delete-selected`**: тело **`DeleteSelectedProjectsRequest`** — **`project_ids`**, **`force`** (по умолчанию **`false`**). Без **`force`** активные проекты считаются **`skipped`**; с **`force`** — revoke + удаление для каждого найденного id.
- **`POST /{id}/reset-status`**: только **`pending`**/**`generating`** → **`status = failed`**, **`error_log = "Manually reset — stale task"`**, **`celery_task_id = None`**, revoke; иначе **400**.

**Backend — `app/api/sites.py`**
- **`DELETE /{site_id}?force=false|true`**: при **`force=False`** и наличии задач/проектов — **409** с **`detail`**: **`message`**, **`task_count`**, **`project_count`**, **`projects: [{ id, name, status }]`**.
- При **`force=True`**: для каждого **`SiteProject`** сайта — revoke по **`celery_task_id`**, удаление задач проекта, удаление проекта; затем **`Task`** с **`target_site_id`**, удаление **`Site`**.

**Frontend**
- **`frontend/src/api/projects.ts`**: **`deleteProject(id, { force })`**, **`deleteSelected(ids, { force })`**, **`resetProjectStatus(id)`**.
- **`frontend/src/api/sites.ts`**: **`delete(id, { force })`**.
- **`ProjectsPage.tsx`**: колонка выбора строк (**`enableRowSelection`** как на **`TasksPage`**), панель **«Удалить выбранные»** / **«Снять выделение»**; во вкладке **Archived** — кнопки **Restore** и **Delete** (корзина); при **400** на удалении — модалка с **Force Delete**; при bulk и **`skipped > 0`** — confirm на повтор с **`force: true`**; **`deleteMutation.mutate`** на деталке проекта — аргумент **`{}`** (требование **TS** / TanStack Query).
- **`ProjectDetailPage.tsx`**: кнопка **Delete** всегда; **Reset stuck status** для **`pending`**/**`generating`**; модалка **Force Delete** после **400**; **`deleteMutation.mutate({})`** для обычного удаления.
- **`SitesPage.tsx`**: при **409** — список блокирующих проектов и кнопка **«Удалить сайт вместе со всеми проектами»** → **`force: true`**.

---
