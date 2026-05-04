# 31 марта 2026 — Pipeline Observability + Isolated Project Pages

**Дата:** 2026-03-31
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Backend (`app/workers/tasks.py`, `app/services/pipeline.py`, `app/services/llm.py`, `app/config.py`, `app/workers/celery_app.py`):**
- Проекты переведены на модель **one page = one Celery task**: отдельные задачи `process_project_page` и `advance_project`, плюс `finalize_project`.
- В `SiteProject` добавлено поле **`generation_started_at`** (миграция `h4c5d6e7f9a1_add_generation_started_at_to_site_projects`) — фактический старт генерации.
- LLM-вызовы получили явный timeout через **`LLM_REQUEST_TIMEOUT`**; в логах — время попытки, время ответа/ошибки, retry-информация.
- В пайплайне добавлен `mark_step_running`: для running-шага сохраняется **`started_at`**; `save_step_result` обновляет `last_heartbeat`.
- В `call_agent` расширено промежуточное логирование (отправка запроса, retry sleep, получение ответа с токенами/стоимостью) и предупреждение при слишком большом контексте (`~>50k` токенов).
- Per-step timeout в `run_phase` теперь опирается на **`STEP_TIMEOUT_MINUTES`**.
- Celery получил soft-limit: **`CELERY_SOFT_TIME_LIMIT`**; `cleanup_stale_tasks` запускается каждые 10 минут и дополнительно проверяет зависшие running-шаги по `started_at`.

**Projects API / UI (`app/api/projects.py`, `frontend/src/pages/ProjectDetailPage.tsx`, `frontend/src/api/projects.ts`):**
- В ответы проекта добавлено поле **`generation_started_at`**.
- Добавлен статус **`awaiting_page_approval`** и endpoint **`POST /api/projects/{id}/approve-page`**.
- Поддержан режим **`PROJECT_PAGE_APPROVAL`**: после завершения страницы проект может ждать ручного подтверждения продолжения.
- На `ProjectDetailPage` добавлен блок **Approve & Continue** для `awaiting_page_approval`; расчёт elapsed/ETA использует `generation_started_at ?? started_at`.

**Task UI (`frontend/src/components/tasks/StepCard.tsx`):**
- Для шагов `running` показывается live-таймер `Running... (Xm Ys)`.
- Для `completed` показывается фактическая длительность по `started_at -> timestamp`.
- Добавлен индикатор `⚠ slow` при выполнении шага дольше 5 минут.
