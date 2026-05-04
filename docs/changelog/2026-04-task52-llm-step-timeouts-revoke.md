# Апрель 2026 — task52: зависания LLM-шагов, таймауты и revoke Celery

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** длинные вызовы (напр. `gpt-5-mini` с reasoning и большим контекстом) + ретраи `generate_text` и exclude-words выходили за **`STEP_TIMEOUT_MINUTES`** / stale в Beat; **`SIGALRM`** в worker-потоке не срабатывал; после **`stale`** / force-fail worker продолжал ждать HTTP.

**Конфиг (`app/config.py`)**
- **`LLM_REQUEST_TIMEOUT`**: дефолт **600** с.
- **`STEP_TIMEOUT_MINUTES`**: **30**; **`PIPELINE_STEP_TIMEOUT_SECONDS`**: **1800**.
- **`LLM_MODEL_TIMEOUTS`**: строка вида `model=seconds,...` — пер- модельный HTTP-таймаут (хелпер **`timeout_for_model`** в **`app/services/llm.py`**).
- **`LLM_MODEL_FALLBACKS`**: строка `primary=fb1|fb2` — в **`generate_text`** в **`extra_body.models`** для OpenRouter provider routing.

**`app/services/llm.py`**
- **`generate_text`**: `timeout=None` → эффективный таймаут через **`timeout_for_model(model)`**; **`max_retries=2`**; backoff для 502/504/timeout **5·(attempt)** (5 с, 10 с); при настроенных fallback — **`extra_body={"models": [model, *fallbacks]}`** без дубля primary в списке fallback.

**`app/services/pipeline/runner.py`**
- **`_call_with_timeout`**: **`ThreadPoolExecutor(max_workers=1)`** + **`future.result(timeout=...)`** → **`StepTimeoutError`** (ветка SIGALRM удалена).
- Перед шагом: **`ctx.step_deadline = monotonic() + timeout_sec`**.

**`app/services/pipeline/context.py`**
- Поле **`step_deadline: float | None`** для бюджета exclude-retry.

**`app/services/pipeline/llm_client.py`**
- Таймаут вызова: **`timeout_for_model(prompt.model)`** вместо фиксированного глобального.
- В лог **`response_received`**: пометка **`⚠ fallback to <actual_model>`**, если ответная модель ≠ запрошенной.
- **`call_agent_with_exclude_validation`**: перед следующим exclude-retry — выход, если **`monotonic() > ctx.step_deadline`**, с предупреждением в лог.

**Celery / БД**
- Модель **`Task.celery_task_id`** (String 64, index), миграция **`x9y8z7w6v5u4_add_celery_task_id_to_tasks.py`**.
- **`app/services/queueing.py`**: **`enqueue_task_generation(db, task)`**, **`revoke_generation_celery_task(id)`**.
- **`app/api/tasks.py`**: все **`process_generation_task.delay`** (кроме **`chain`** в start-all / start-selected) заменены на **`enqueue_task_generation`**; при **`POST .../force-status`** с **`action=fail`** — **`revoke_generation_celery_task`** до смены статуса.
- **`process_generation_task`**: в начале записывает **`task.celery_task_id = self.request.id`**.
- **`process_project_page`**: перед **`run_pipeline`** — то же для **`project_task`** (страницы проекта).
- **`cleanup_stale_tasks`**: после перевода в **`stale`** (heartbeat и step-running timeout) — **`celery_app.control.revoke(..., terminate=True, signal="SIGTERM")`**, если **`celery_task_id`** задан.

**Тесты:** **`tests/services/test_runner_call_timeout.py`** (main thread + worker thread), **`tests/services/test_llm_timeouts_fallbacks.py`**.

**Оговорка:** **`future.result(timeout)`** не убивает поток с активным HTTP; прерывание обеспечивают httpx-таймаут и revoke.

---
