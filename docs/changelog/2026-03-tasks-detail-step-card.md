# Март 2026 — Задачи (Tasks), деталь задачи, шаги pipeline (StepCard)

**Дата:** 2026-03-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Цель:** выборочный запуск задач, человекочитаемые шаги SERP/Scraping, табы результата/промптов/переменных для LLM-шагов, рабочие execution logs, без дублирующих табов.

**Backend (`app/api/tasks.py`):**
- `POST /api/tasks/start-selected` — тело `{ "task_ids": ["uuid", ...] }`; выбираются только задачи со статусом **`pending`** и **`project_id is null`**; порядок как у очереди (`priority` DESC, `created_at` ASC); запуск через Celery **`chain`** (последовательно). Невалидные UUID в списке пропускаются.
- `GET /api/tasks/{id}` — в ответ добавлены **`country`**, **`language`** (для карточки справа на деталке задачи).
- `DELETE /api/tasks/{id}/cache` — ручная инвалидация SERP-кэша для задачи.

**Frontend — `TasksPage.tsx`:**
- Первая колонка таблицы: чекбоксы только для **`pending`**; в заголовке — **Select all** по видимым pending-задачам (с `indeterminate`).
- Состояние выбора: `useState<Set<string>>`.
- Кнопка **Start Selected (N)** рядом с Start Next / Start All; вызывает `tasksApi.startSelected`.

**Frontend — `TaskDetailPage.tsx`:**
- Два таба: **Pipeline Execution** и **Execution Logs** (убраны отдельные табы SERP Data и Prompts Debug — детали в шагах pipeline).
- Логи: поля из `add_log` — **`ts`**, **`msg`**, **`level`**, **`step`** (без `timestamp`/`message`).
