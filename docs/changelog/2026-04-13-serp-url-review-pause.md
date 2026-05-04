# 13 апреля 2026 — Пауза после SERP: ревью и редактирование URL конкурентов

**Дата:** 2026-04-13
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** между SERP и scraping пользователь должен иметь возможность убрать «мусорные» URL и добавить свои (например из Ahrefs). Аналогия с паузой **`image_review`**, но для одиночных (**не проектных**) задач и со статусом задачи **`paused`**.

**Поведение**
- При **`run_pipeline(..., auto_mode=False)`** после успешного **`save_step_result`** для шага **`serp`** в **`phase_serp`**: в **`step_results`** пишется **`_pipeline_pause: { "active": true, "reason": "serp_review" }`**, **`task.status = paused`**, пайплайн **не** переходит к **`phase_scraping`** (после **`run_phase`** для SERP выполняется **`return`** из **`run_pipeline`**).
- При **`auto_mode=True`** (страницы проекта) пауза **не** выставляется — поведение проектов без изменений.
- В начале **`run_pipeline`** обработка активной паузы **`serp_review`** без **`_serp_urls_approved`**: для ручной задачи — повторный лог и **`return`** (статус **`paused`**); для **`auto_mode`** — автоснятие паузы и пометка approved (защита от неконсистентного состояния).

**База данных и модель**
- Enum PostgreSQL **`task_status`**: новое значение **`paused`**. Миграция **`m9n0o1p2q3re_add_task_status_paused`**: **`ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'paused'`**.
- Модель **`app/models/task.py`**: **`task_status_enum`** включает **`paused`**.

**API (`app/api/tasks.py`)**
- **`GET /api/tasks/{task_id}/serp-urls`** — список URL из **`task.serp_data`** с обогащением из **`organic_results`** (title, description, position/rank, domain, **`manually_added`**), плюс **`paused`** (активна ли пауза **`serp_review`**) и **`keyword`**.
- **`POST /api/tasks/{task_id}/approve-serp-urls`** — тело **`{ "urls": ["https://...", ...] }`** (непустой список). Требуется активная пауза **`serp_review`**; обновляются **`serp_data.urls`** и **`serp_data.organic_results`** (новые URL получают заглушку с **`manually_added: true`**); **`_pipeline_pause.active = false`**, **`_serp_urls_approved = true`**, **`status = pending`**, **`process_generation_task.delay`**.
- **`POST .../force-status`**: допускается также **`paused`** (наряду с **`processing`**, **`stale`**).
- **`POST .../rerun-step`**: допускается также **`paused`**.

**Frontend**
- **`frontend/src/components/tasks/SerpUrlsReviewer.tsx`** — таблица URL, удаление, ручное добавление (**`http://` / `https://`**), кнопка продолжения, бейдж **Manual** для **`manually_added`**.
- **`frontend/src/api/tasks.ts`** — **`getSerpUrls`**, **`approveSerpUrls`**.
- **`TaskDetailPage`**: блок при **`status === "paused"`** и **`_pipeline_pause.reason === "serp_review"`**; опрос задачи каждые 3 с и для **`paused`**; фильтр статуса **Paused** на **`TasksPage`**; **`StatusBadge`** / тип **`Task`** — **`paused`**.

**`PipelineContext` (`pipeline.py`)** — поле **`auto_mode`**, задаётся из **`run_pipeline`**.

---
