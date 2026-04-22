# План: устранение зависаний LLM-шагов (improver и другие)

## Context
На вкладке Project задача зависала на шаге `improver`: `gpt-5-mini` с reasoning и большим контекстом (38k+14k tokens) отвечает 5+ мин, после этого идёт retry по exclude-words, и суммарное время выходит за `STEP_TIMEOUT_MINUTES=15`. Beat-детектор пишет «Task marked stale», но Celery-процесс продолжает ждать HTTP-ответ, и UI показывает «висит».

Разбор лога одной задачи показал: `LLM_REQUEST_TIMEOUT=300` с `max_retries=3` даёт worst-case ~16 мин на один LLM-вызов; плюс exclude-retry удваивает. На это накладывается возможная нестабильность роутинга OpenAI в OpenRouter.

Четыре фикса (A–D) закрывают разные уровни: таймауты и параметры ретраев (A, C), устойчивость к падению провайдера (B), согласованность БД-статусов с реальным процессом (D).

## Критические файлы
- [app/config.py](app/config.py) — таймауты и новые настройки.
- [app/services/llm.py](app/services/llm.py) — OpenRouter-клиент, общая функция `generate_text`, ретраи.
- [app/services/pipeline/llm_client.py](app/services/pipeline/llm_client.py) — per-agent вызов, exclude-retry.
- [app/services/pipeline/runner.py](app/services/pipeline/runner.py) — `_call_with_timeout`, пер-шаговый таймаут.
- [app/workers/tasks.py](app/workers/tasks.py) — `cleanup_stale_tasks`, постановка в очередь (`process_generation_task`, `process_site_project`).
- [app/api/tasks.py](app/api/tasks.py) / [app/api/projects.py](app/api/projects.py) — места, где делается `.delay(...)` (сохранять `celery_task_id`).
- [app/models/task.py](app/models/task.py) — добавить колонку `celery_task_id`.
- Миграция Alembic для новой колонки.

---

## A. Таймауты и per-model override (самая короткая правка, один симптом уберёт)

### A.1 Поднять дефолтный LLM-таймаут
- В [app/config.py:28](app/config.py:28): `LLM_REQUEST_TIMEOUT: int = 600`.
- В [app/config.py:52](app/config.py:52): `STEP_TIMEOUT_MINUTES: int = 30` (иначе step-timeout меньше одного LLM-вызова).

### A.2 Per-model таймаут
- В [app/config.py](app/config.py) добавить:
  ```python
  LLM_MODEL_TIMEOUTS: str = ""  # "openai/gpt-5-mini=900,openai/gpt-5=900,perplexity/sonar=300"
  ```
- Хелпер (можно прямо в `app/services/llm.py` выше `get_openai_client`):
  ```python
  def timeout_for_model(model: str) -> int:
      raw = (settings.LLM_MODEL_TIMEOUTS or "").strip()
      if raw:
          for pair in raw.split(","):
              k, _, v = pair.partition("=")
              if k.strip() == model and v.strip().isdigit():
                  return int(v)
      return settings.LLM_REQUEST_TIMEOUT
  ```
- В `generate_text` ([llm.py:37](app/services/llm.py:37)) поменять сигнатуру: `timeout: int | None = None`, внутри `timeout = timeout or timeout_for_model(model)`.
- `OpenAI(..., timeout=...)` ([llm.py:18-22](app/services/llm.py:18)) оставить на `settings.LLM_REQUEST_TIMEOUT` как ceiling клиента; per-call `timeout=` на kwargs `.create()` уже переопределяет.

### A.3 Разумный max_retries и sleep
- В [llm.py:35](app/services/llm.py:35): `max_retries: int = 2` вместо 3.
- В [llm.py:165-167](app/services/llm.py:165) для `upstream_timeout_or_gateway` поставить sleep `5/10` вместо `15/30/45`: `sleep_seconds = 5 * (retries + 1)`.
- Rate-limit (60/120/180) оставить — там длинные паузы оправданы.

---

## B. Fallback-модель через OpenRouter provider routing

### B.1 Конфигурация
- В [app/config.py](app/config.py):
  ```python
  LLM_MODEL_FALLBACKS: str = ""  # "openai/gpt-5-mini=openai/gpt-5|anthropic/claude-sonnet-4.6"
  ```
  Ключ — primary, значение — pipe-разделённый список fallbacks в порядке приоритета.
- Хелпер `fallbacks_for_model(model) -> list[str]` рядом с `timeout_for_model`.

### B.2 Прокидывание в запрос
В [llm.py:64-83](app/services/llm.py:64), собирая `kwargs`, добавить:
```python
fallbacks = fallbacks_for_model(model)
if fallbacks:
    kwargs["extra_body"] = {"models": [model, *fallbacks]}
```
OpenRouter сам переключится на fallback при таймауте/ошибке провайдера (см. `models` в OpenRouter API). `response.model` в ответе уже содержит реально сработавшую модель — оно и так логируется ([llm.py:135](app/services/llm.py:135)) и возвращается наверх.

### B.3 Лог
В `progress_callback("response_received", …)` уже есть `model=actual_model`. В `add_log` в [llm_client.py:196-202](app/services/pipeline/llm_client.py:196) добавить пометку, если `actual_model != requested_model`: «⚠ fallback to <actual>». Сделает диагностику падений OpenAI явной в UI.

---

## C. Step-timeout, который действительно прерывает

### C.1 Заменить SIGALRM на ThreadPoolExecutor
В [app/services/pipeline/runner.py:90-112](app/services/pipeline/runner.py:90) переписать `_call_with_timeout`:
```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

def _call_with_timeout(step, ctx, timeout_sec):
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"step-{step.name}") as ex:
        future = ex.submit(step.run, ctx)
        try:
            return future.result(timeout=timeout_sec)
        except FuturesTimeout:
            # не можем реально убить httpx-сокет изнутри Python, но прервём ожидание
            # самой внутренностью LLM httpx-таймаут всё равно сработает за счёт A.1
            raise StepTimeoutError(f"Step {step.name} timed out after {timeout_sec}s")
```
Плюсы: работает и в prefork, и в threaded Celery; чёткий `StepTimeoutError`, который уже корректно обрабатывается на [runner.py:144-147](app/services/pipeline/runner.py:144) (`save_step_result(..., status="failed")`).

Оговорка: `future.result(timeout)` не убивает поток — он продолжает работать в фоне до ответа HTTP. Это ок, потому что (A) внутренний httpx-таймаут теперь адекватный, (B) worker всё равно скоро уйдёт, потому что runner бросил исключение и шаг помечен failed.

### C.2 Удалить SIGALRM-ветку
Удалить весь блок `if hasattr(signal, "SIGALRM")` и импорт `signal` из [runner.py](app/services/pipeline/runner.py). Проверить, что `signal` больше нигде в файле не используется.

### C.3 Согласовать бюджет ретраев с таймаутом шага
В [llm_client.py:224-306](app/services/pipeline/llm_client.py:224) exclude-retry делает ещё один полный `generate_text`. Добавить проверку остаточного wall-clock-бюджета: передавать deadline (`time.monotonic() + timeout_sec`) и в цикле проверять `if monotonic() > deadline: break`. Опора: `ctx.step_deadline` (опционально, чтобы не ломать сигнатуру — берём `settings.STEP_TIMEOUT_MINUTES * 60 - уже прошло`).

---

## D. Beat-детектор реально убивает Celery-task

### D.1 Хранить celery_task_id у Task
- **Модель**: в [app/models/task.py](app/models/task.py) добавить `celery_task_id = Column(String(64), nullable=True, index=True)`.
- **Миграция Alembic**: новая ревизия, `op.add_column('tasks', sa.Column('celery_task_id', sa.String(64), nullable=True))` + `op.create_index('ix_tasks_celery_task_id', 'tasks', ['celery_task_id'])`.

### D.2 Сохранять id при постановке в очередь
Все места `process_generation_task.delay(str(task.id))` в [app/api/tasks.py:296,333,367,665,706,858,982,1072](app/api/tasks.py:296) обернуть одной функцией:
```python
# app/services/queueing.py
def enqueue_task(db, task: Task) -> str:
    res = process_generation_task.delay(str(task.id))
    task.celery_task_id = res.id
    db.commit()
    return res.id
```
Заменить все call-site. Аналогично для `process_site_project.delay(...)` в [app/api/projects.py](app/api/projects.py) — но там уже есть `result = process_site_project.delay(...)` в :623, :1048, где `result.id` доступен, нужно только сохранить в `SiteProject.celery_task_id` (если не хочется — D.2 ограничить только Task’ами; проектные задачи ретраят сами себя и не висят на LLM).

### D.3 Revoke при stale
В [app/workers/tasks.py:507-523](app/workers/tasks.py:507) после `task.status = "stale"` и до `break`:
```python
from app.workers.celery_app import celery_app
if task.celery_task_id:
    try:
        celery_app.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")
    except Exception as e:
        print(f"revoke failed for task {task.id}: {e}")
```
SIGTERM даёт процессу шанс на finally (rollback, логи). Если не уйдёт — следующая итерация beat (через 10 мин) уже ничего не добавит. Если хочется жёстче — `signal="SIGKILL"`, но тогда никакой cleanup не сработает.

### D.4 Force-fail API тоже должен revoke
В [app/api/tasks.py:721-745](app/api/tasks.py:721) в ветке `action == "fail"` добавить тот же revoke. Сейчас пользователь жмёт «Force fail» — БД-статус меняется, но worker продолжает жрать токены. После правки — прерывание реальное.

---

## Порядок выкатки и верификация

### Стадия 1 (минут 10 работы, самая высокая ценность)
Фиксы A.1, A.3, C.1, C.2. Без миграций. Перезапуск worker + beat.

**Verify:**
- Юнит-тест: `_call_with_timeout` с `step.run = lambda ctx: time.sleep(2)` и `timeout_sec=1` должен падать `StepTimeoutError` (в main-thread **и** в `threading.Thread.run()`, для проверки независимости от SIGALRM).
- Интеграционный: мок `generate_text`, который спит 700 с при `LLM_REQUEST_TIMEOUT=600`. Шаг должен упасть как failed через ≤`STEP_TIMEOUT_MINUTES*60`.
- Ручной: новая задача с gpt-5-mini на Luxury Casino. В логе worker `[LLM] Attempt 1/2, timeout=900s` (если поставил per-model), шаг проходит без stale-marker.

### Стадия 2 (B — провайдер-резерв)
Фиксы A.2, B. Задать `LLM_MODEL_TIMEOUTS` и `LLM_MODEL_FALLBACKS` в `.env`.

**Verify:**
- Мок OpenRouter, возвращающий 502 для `openai/gpt-5-mini`. После правки B логи worker показывают actual_model = fallback; в UI лог «⚠ fallback to anthropic/claude-sonnet-4.6».
- Проверить, что в `kwargs["extra_body"]["models"]` не дублируется primary, если он уже в fallbacks.

### Стадия 3 (D — revoke)
Миграция + D.1–D.4. Нужен downtime на миграцию (колонка nullable, так что совместимо).

**Verify:**
- Создать задачу, в консоли: `celery -A app.workers.celery_app inspect active` — записать task_id; оно должно совпадать с `tasks.celery_task_id` в БД.
- Запустить задачу, до завершения `curl -X POST /api/tasks/<id>/force-status -d '{"action":"fail"}'`. Worker-лог должен показать `Task revoked`/`SoftTimeLimitExceeded`/`WorkerLostError`; LLM-запрос не должен завершиться нормально.
- Дождаться реального зависания (искусственно: мок с `time.sleep(2000)`), проверить что через `STALE_TASK_TIMEOUT_MINUTES` beat автоматически делает revoke и процесс умирает.

---

## Вне scope (осознанные отказы)
- Не меняем Celery-пул на gevent/eventlet. Prefork + httpx-таймаут + future-таймаут достаточно.
- Не делаем async переход в pipeline — слишком широкий blast radius.
- Не переносим exclude-words retry в отдельную Celery-подзадачу — избыточно.
- Не добавляем провайдерский retry на уровне OpenRouter через `provider.order` — `models` fallback закрывает тот же кейс проще.
