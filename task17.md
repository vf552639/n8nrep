# ТЗ: Изоляция страниц проекта — одна страница = один Celery task

> **Приоритет:** CRITICAL  
> **Исполнитель:** antigravity  
> **Дата:** 2026-03-31  
> **Оценка:** 2-3 дня  

---

## Проблема

Текущая архитектура `process_site_project` обрабатывает **все страницы в одном Celery task**, в одном цикле `for`. Это приводит к:

1. **Утечка памяти** — SQLAlchemy session накапливает объекты Task, step_results (50-100KB JSONB на задачу), competitors_text (15-50KB), PipelineContext. После первой страницы данные НЕ освобождаются. Вторая страница работает медленнее, третья может не запуститься.

2. **Timeout на весь проект** — `CELERY_TASK_TIME_LIMIT = 900` секунд (15 мин) — это на ВСЕ страницы в одном task, а не на одну. Первая страница занимает 3-5 мин, вторая из-за замедления 7-8 мин → Celery убивает worker.

3. **Невозможность диагностики** — при зависании на второй странице нет информации какой именно LLM-вызов завис и сколько времени прошло.

4. **Таймер на фронте врёт** — `started_at` устанавливается при создании проекта, а не при старте генерации.

---

## Решение: Архитектура "Page-per-Task"

Вместо одного Celery task с циклом — **каждая страница обрабатывается в отдельном Celery task** с чистой сессией БД и изолированной памятью. Лёгкий координатор (`process_project_page`) запускает следующую страницу после завершения предыдущей.

### Как работает каннибализация (уже решено)

`ContentDeduplicator` записывает анкоры (заголовки, ключевые фразы) в таблицу `project_content_anchors` после каждой статьи. Функция `get_already_covered()` читает их из БД при старте следующей страницы через переменную `{{already_covered_topics}}`. Это **идеально работает** с новой архитектурой, потому что каждый новый Celery task получает свежие данные из БД.

---

## Задача 1. Рефакторинг `process_site_project` → координатор + page worker

### Файл: `app/workers/tasks.py`

#### 1.1. Новый Celery task: `process_project_page`

Создать новый task, который обрабатывает **одну страницу** проекта:

```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def process_project_page(self, project_id: str, page_index: int):
    """
    Обрабатывает одну страницу проекта.
    После завершения — вызывает координатор для запуска следующей.
    Полная изоляция: своя DB session, свой PipelineContext.
    """
```

**Логика внутри:**

1. Открыть **новую** `SessionLocal()`.
2. Загрузить `project`, `pages` (только одну по `page_index`).
3. Проверить `project.stopping_requested` → если True, поставить `project.status = "stopped"` и вернуться.
4. Создать или найти существующий `Task` для этой страницы (текущая логика из цикла `for`).
5. Записать лог: `"Starting page {page_index+1}/{n_pages}: '{page.page_title}'"`.
6. Замерить время: `t0 = time_module.monotonic()`.
7. Вызвать `run_pipeline(db, str(task.id), auto_mode=True)` — **точно как сейчас**.
8. После завершения:
   - Если `task.status == "completed"` → записать лог с временем и стоимостью.
   - Если failed → записать в лог, добавить в `project.error_log` (как JSON-массив ошибок).
9. **Закрыть** `db.close()`.
10. Вызвать координатор: `advance_project.delay(project_id)`.

#### 1.2. Новый Celery task: `advance_project` (координатор)

Лёгкий task без тяжёлой логики — только решает, запускать ли следующую страницу:

```python
@celery_app.task(bind=True)
def advance_project(self, project_id: str):
    """
    Координатор проекта. Определяет следующую незавершённую страницу
    и запускает process_project_page. Если все страницы готовы — финализирует.
    """
```

**Логика:**

1. Открыть **новую** `SessionLocal()`.
2. Загрузить `project`.
3. Проверить `project.stopping_requested` → если True, финализировать как "stopped".
4. Проверить `PROJECT_PAGE_APPROVAL` (из settings) → если True и предыдущая страница completed, поставить `project.status = "awaiting_page_approval"`, записать лог, `return`. (см. Задачу 5).
5. Получить список `BlueprintPage` для этого проекта.
6. Получить `completed_page_ids` из Task-ов проекта (как сейчас).
7. Найти **первую** страницу, которая НЕ в `completed_page_ids` → это `next_page_index`.
8. Если `next_page_index` найден → `process_project_page.delay(project_id, next_page_index)`.
9. Если все страницы completed → вызвать `finalize_project(db, project_id)`.
10. Закрыть `db.close()`.

#### 1.3. Вынести финализацию: `finalize_project(db, project_id)`

Вынести текущий код финализации из конца `process_site_project` в отдельную функцию:

```python
def finalize_project(db, project_id: str):
    """
    Финализация проекта: build_site, подсчёт стоимости, установка статуса.
    Вызывается из advance_project когда все страницы готовы.
    """
```

**Содержимое — точная копия текущего кода** из `process_site_project` после цикла `for`:
- `build_site(db, project_id)`
- Подсчёт `total_cost`, `ok`, `fail_n`
- Установка `project.status = "completed"` (или "completed" с `error_log` если были failed pages)
- `project.completed_at = datetime.utcnow()`
- Запись лога `"Project completed: ..."`

#### 1.4. Переписать `process_site_project` как тонкий стартер

Существующий `process_site_project` становится **стартером** — только инициализация:

```python
@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def process_site_project(self, project_id: str):
    """
    Стартер проекта. Инициализирует статус и запускает координатор.
    Вся тяжёлая работа — в process_project_page (per-page isolation).
    """
    db = SessionLocal()
    try:
        project = db.query(SiteProject).filter(SiteProject.id == project_id).first()
        if not project:
            print(f"Project {project_id} not found!")
            return

        project.status = "generating"
        project.generation_started_at = datetime.utcnow()  # новое поле, см. Задачу 4
        if project.started_at is None:
            project.started_at = datetime.utcnow()
        
        _append_project_log(db, project, "Project started. Launching page-by-page generation.")
        db.commit()

        # Запускаем координатор — он найдёт первую незавершённую страницу
        advance_project.delay(project_id)
    except Exception as exc:
        if project:
            project.status = "failed"
            project.error_log = str(exc)
            project.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
```

#### 1.5. Что удалить

Из `process_site_project` удалить:
- Весь цикл `for i, page in enumerate(pages):`
- Всю логику создания Task-ов
- Вызов `run_pipeline` напрямую
- Финализацию (`build_site`, подсчёт стоимости)
- Все `failed_pages` tracking (перенести в `process_project_page`)

---

## Задача 2. Per-step и per-LLM-call timeouts

### Файл: `app/config.py`

Добавить новые настройки:

```python
# Timeouts
LLM_REQUEST_TIMEOUT: int = 300          # 5 минут на один LLM-вызов
CELERY_TASK_TIME_LIMIT: int = 1800      # 30 минут (было 900) — на одну страницу теперь
CELERY_SOFT_TIME_LIMIT: int = 1500      # 25 минут — soft limit для graceful shutdown
STEP_TIMEOUT_MINUTES: int = 15          # макс. время на один шаг pipeline
```

### Файл: `app/services/llm.py`

#### 2.1. Добавить timeout в OpenAI клиент

В функции `get_openai_client()`:

```python
# БЫЛО:
_openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

# СТАЛО:
_openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
    timeout=settings.LLM_REQUEST_TIMEOUT,  # <-- ДОБАВИТЬ
)
```

#### 2.2. Добавить тайминги в логи LLM-вызовов

В функции `generate_text()`, в цикле while:

**Перед** `raw_response = client.chat.completions.with_raw_response.create(**kwargs)`:
```python
attempt_start = time.monotonic()
print(f"[LLM] Attempt {retries+1}/{max_retries}, model={model}, timeout={settings.LLM_REQUEST_TIMEOUT}s")
```

**После** получения ответа (перед `return`):
```python
elapsed = time.monotonic() - attempt_start
print(f"[LLM] Response OK in {elapsed:.1f}s, model={actual_model}, "
      f"tokens={usage_info}")
```

**В блоке except**, добавить elapsed:
```python
elapsed = time.monotonic() - attempt_start
print(f"[LLM] Error after {elapsed:.1f}s (Attempt {retries+1}/{max_retries}): {error_msg}")
```

### Файл: `app/workers/celery_app.py`

Добавить soft time limit:

```python
celery_app.conf.update(
    ...
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_SOFT_TIME_LIMIT,  # <-- ДОБАВИТЬ
    ...
)
```

---

## Задача 3. Расширенное логирование для диагностики зависаний

### Файл: `app/services/pipeline.py`

#### 3.1. Записывать `started_at` в step_results при запуске шага

Найти функцию `save_step_result`. Во всех вызовах `save_step_result(..., status="running")` в каждой `phase_*` функции — добавлять `started_at`:

Создать обёрточную функцию (или модифицировать `save_step_result`):

```python
def mark_step_running(db, task, step_key, model_name=None):
    """Помечает шаг как running с timestamp и моделью для диагностики."""
    import datetime
    step_data = {
        "status": "running",
        "started_at": datetime.datetime.utcnow().isoformat(),
    }
    if model_name:
        step_data["model"] = model_name
    
    step_results = dict(task.step_results or {})
    existing = step_results.get(step_key, {})
    if isinstance(existing, dict):
        existing.update(step_data)
    else:
        existing = step_data
    step_results[step_key] = existing
    task.step_results = step_results
    task.last_heartbeat = datetime.datetime.utcnow()
    db.commit()
```

**Использовать** эту функцию вместо `save_step_result(ctx.db, ctx.task, STEP_XXX, result=None, status="running")` в каждом `phase_*`. Передавать `model_name` из промпта, если доступен.

#### 3.2. Обновлять heartbeat после завершения шага

В функции `save_step_result` — добавить в конце:

```python
task.last_heartbeat = datetime.datetime.utcnow()
db.commit()
```

#### 3.3. Логировать размер контекста перед каждым LLM-вызовом

В `call_agent` (строка с `print(f"[call_agent] {agent_name} | model=...")`) — уже есть. Убедиться что total_chars логируется корректно. Добавить оценку токенов:

```python
est_tokens = total_chars // 4
if est_tokens > 50000:
    add_log(ctx.db, ctx.task, 
            f"⚠️ Large context for {agent_name}: ~{est_tokens} tokens estimated",
            level="warn", step=agent_name)
```

---

## Задача 4. Исправить таймер проекта

### Файл: `app/models/project.py`

Добавить новое поле в `SiteProject`:

```python
generation_started_at = Column(DateTime, nullable=True, 
    comment="Фактическое время начала генерации (не время создания)")
```

### Файл: Alembic миграция

Создать миграцию:

```bash
alembic revision --autogenerate -m "add_generation_started_at_to_projects"
```

Миграция должна добавить колонку `generation_started_at` (nullable DateTime) в `site_projects`.

### Файл: `app/workers/tasks.py`

В новом `process_site_project` (стартер) — устанавливать `generation_started_at`:

```python
project.generation_started_at = datetime.utcnow()
```

**НЕ перезаписывать** при resume — только если `generation_started_at is None`.

### Файл: `app/api/projects.py`

В функции где формируется ответ с данными проекта — добавить `generation_started_at` в JSON:

```python
"generation_started_at": project.generation_started_at.isoformat() if project.generation_started_at else None,
```

### Файл: `frontend/src/pages/ProjectDetailPage.tsx`

Заменить расчёт `elapsedSec`:

```typescript
// БЫЛО:
const elapsedSec =
    project.started_at != null
      ? (nowTick - new Date(project.started_at).getTime()) / 1000
      : null;

// СТАЛО:
const elapsedSec =
    (project.generation_started_at ?? project.started_at) != null
      ? (nowTick - new Date(project.generation_started_at ?? project.started_at).getTime()) / 1000
      : null;
```

---

## Задача 5. Режим "Page-by-Page Approval"

### Файл: `app/config.py`

Добавить настройку:

```python
PROJECT_PAGE_APPROVAL: bool = False  # Если True — после каждой страницы ждём аппрув
```

### Файл: `app/workers/tasks.py`

В `advance_project` — перед запуском следующей страницы проверять:

```python
if settings.PROJECT_PAGE_APPROVAL:
    # Проверяем, есть ли только что завершённая страница
    last_completed = db.query(Task).filter(
        Task.project_id == project.id,
        Task.status == "completed"
    ).order_by(Task.updated_at.desc()).first()
    
    if last_completed and not project_meta.get("page_approved"):
        project.status = "awaiting_page_approval"
        _append_project_log(db, project, 
            f"Page '{last_completed.main_keyword}' completed. "
            f"Waiting for approval before next page.")
        db.commit()
        db.close()
        return
```

### Файл: `app/api/projects.py`

Добавить endpoint:

```python
@router.post("/{id}/approve-page")
def approve_page(id: str, db: Session = Depends(get_db)):
    """Одобряет последнюю страницу и продолжает генерацию проекта."""
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.status != "awaiting_page_approval":
        raise HTTPException(status_code=400, 
            detail=f"Project is not awaiting approval (status: {project.status})")
    
    project.status = "generating"
    _append_project_log(db, project, "Page approved. Continuing generation.")
    db.commit()
    
    advance_project.delay(str(project.id))
    
    return {"msg": "Page approved, generation resumed"}
```

### Файл: `frontend/src/pages/ProjectDetailPage.tsx`

Добавить кнопку, когда `project.status === "awaiting_page_approval"`:

```tsx
{project.status === "awaiting_page_approval" && (
  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between">
    <div>
      <p className="font-semibold text-amber-900">Page completed — waiting for approval</p>
      <p className="text-sm text-amber-700 mt-1">
        Review the generated page, then approve to continue.
      </p>
    </div>
    <button
      onClick={() => approvePageMutation.mutate()}
      className="px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700"
    >
      Approve & Continue
    </button>
  </div>
)}
```

Добавить мутацию:

```typescript
const approvePageMutation = useMutation({
    mutationFn: () => projectsApi.approvePage(id!),
    onSuccess: () => {
      toast.success("Page approved, generation resumed");
      queryClient.invalidateQueries({ queryKey: ["project", id] });
    },
    onError: () => toast.error("Approval failed"),
});
```

### Файл: `frontend/src/api/projects.ts`

Добавить метод API:

```typescript
approvePage: (id: string) => api.post(`/projects/${id}/approve-page`).then(r => r.data),
```

### Файл: `app/api/projects.py` — StatusBadge

Добавить `"awaiting_page_approval"` в допустимые статусы проекта. Обновить комментарий у поля `status` в модели.

### Файл: `frontend/src/components/common/StatusBadge.tsx`

Добавить обработку нового статуса:

```typescript
"awaiting_page_approval": "text-amber-700 bg-amber-100"
```

С label: `"Awaiting Approval"`.

---

## Задача 6. Auto-recovery зависших шагов

### Файл: `app/workers/tasks.py`

#### 6.1. Улучшить `cleanup_stale_tasks`

Добавить проверку `started_at` в step_results:

```python
@celery_app.task
def cleanup_stale_tasks():
    db = SessionLocal()
    from app.models.task import Task
    from datetime import datetime, timedelta
    
    try:
        step_timeout = timedelta(minutes=settings.STEP_TIMEOUT_MINUTES)
        now = datetime.utcnow()
        
        # 1. Текущая логика: heartbeat-based stale detection (30 мин)
        stale_threshold = now - timedelta(minutes=30)
        # ... (существующий код) ...
        
        # 2. НОВОЕ: step-level timeout detection
        processing_tasks = db.query(Task).filter(
            Task.status == "processing"
        ).all()
        
        for task in processing_tasks:
            step_results = task.step_results or {}
            for step_name, step_data in step_results.items():
                if step_name.startswith("_"):  # skip meta-keys
                    continue
                if not isinstance(step_data, dict):
                    continue
                if step_data.get("status") != "running":
                    continue
                
                started_at_str = step_data.get("started_at")
                if not started_at_str:
                    continue
                
                try:
                    started_at = datetime.fromisoformat(started_at_str)
                except (ValueError, TypeError):
                    continue
                
                if now - started_at > step_timeout:
                    # Шаг завис — помечаем как failed
                    step_data["status"] = "failed"
                    step_data["error"] = f"Step timed out after {settings.STEP_TIMEOUT_MINUTES} minutes"
                    task.step_results = dict(step_results)  # trigger SQLAlchemy change
                    task.status = "stale"
                    task.error_log = f"Step '{step_name}' timed out after {settings.STEP_TIMEOUT_MINUTES}min"
                    
                    add_log(db, task, 
                        f"⏰ Step '{step_name}' timed out ({settings.STEP_TIMEOUT_MINUTES}min). Task marked stale.",
                        level="error", step=step_name)
                    break  # одного зависшего шага достаточно
        
        db.commit()
    finally:
        db.close()
```

#### 6.2. Увеличить частоту cleanup

### Файл: `app/workers/celery_app.py`

```python
# БЫЛО:
'cleanup-stale-tasks-every-hour': {
    'task': 'app.workers.tasks.cleanup_stale_tasks',
    'schedule': crontab(minute=0, hour='*'),
},

# СТАЛО:
'cleanup-stale-tasks-every-10min': {
    'task': 'app.workers.tasks.cleanup_stale_tasks',
    'schedule': crontab(minute='*/10'),
},
```

---

## Задача 7. Фронтенд — live-таймер для running-шагов

### Файл: `frontend/src/components/tasks/StepCard.tsx`

Если `step.status === "running"` и есть `started_at` в данных — показывать live-таймер:

```tsx
// Внутри компонента StepCard
const [elapsed, setElapsed] = useState(0);

useEffect(() => {
  if (step.status !== "running") return;
  
  const startedAt = step.started_at || step.result_data?.started_at;
  if (!startedAt) return;
  
  const startTime = new Date(startedAt).getTime();
  
  const interval = setInterval(() => {
    setElapsed(Math.floor((Date.now() - startTime) / 1000));
  }, 1000);
  
  return () => clearInterval(interval);
}, [step.status, step.started_at]);

// В JSX, рядом со спиннером:
{step.status === "running" && elapsed > 0 && (
  <span className="text-xs text-blue-600 font-mono ml-2">
    {Math.floor(elapsed / 60)}m {elapsed % 60}s
  </span>
)}
```

Также добавить **warning-подсветку** если шаг работает дольше 5 минут:

```tsx
{step.status === "running" && elapsed > 300 && (
  <span className="text-xs text-amber-600 font-medium ml-1">⚠ slow</span>
)}
```

---

## Порядок реализации

| #   | Задача                                      | Зависимости | Оценка    |
| --- | ------------------------------------------- | ----------- | --------- |
| 1   | **Задача 2** — Timeouts (LLM + Celery)      | Нет         | 2-3 часа  |
| 2   | **Задача 3** — Расширенное логирование      | Нет         | 2-3 часа  |
| 3   | **Задача 4** — Таймер проекта + миграция    | Нет         | 1-2 часа  |
| 4   | **Задача 1** — Рефакторинг на Page-per-Task | Задачи 2-3  | 6-8 часов |
| 5   | **Задача 6** — Auto-recovery зависших шагов | Задача 3    | 2-3 часа  |
| 6   | **Задача 7** — Live-таймер на фронте        | Задача 3    | 1-2 часа  |
| 7   | **Задача 5** — Page-by-Page Approval        | Задача 1    | 3-4 часа  |

**Рекомендация:** Задачи 2, 3, 4 можно делать параллельно/независимо. Задача 1 — ключевая, на неё уйдёт больше всего времени. Задача 5 — опциональная, но очень полезная.

---

## Чеклист тестирования

### После Задачи 1 (Page-per-Task):

- [ ] Проект из 3 страниц запускается и все 3 страницы генерируются
- [ ] Каждая страница — отдельный Celery task в логах worker'а
- [ ] Memory не растёт между страницами (проверить `docker stats`)
- [ ] `ContentDeduplicator` передаёт анкоры предыдущих страниц в следующую
- [ ] Resume работает: если проект остановлен после 2/5 страниц → при перезапуске продолжает с 3-й
- [ ] `stopping_requested` работает между страницами
- [ ] Логи проекта показывают время и стоимость каждой страницы

### После Задачи 2 (Timeouts):

- [ ] LLM-вызов не висит дольше 5 минут (проверить в логах worker'а)
- [ ] При timeout — retry срабатывает корректно
- [ ] Celery soft time limit не убивает task раньше 25 минут

### После Задачи 5 (Page Approval):

- [ ] При `PROJECT_PAGE_APPROVAL=True` — проект останавливается после каждой страницы
- [ ] Кнопка "Approve & Continue" возобновляет генерацию
- [ ] При `PROJECT_PAGE_APPROVAL=False` — поведение как обычно (без пауз)

---

## Файлы, которые нужно изменить (сводка)

| Файл                                             | Что менять                                             |
| ------------------------------------------------ | ------------------------------------------------------ |
| `app/workers/tasks.py`                           | Главный рефакторинг: новые tasks, координатор, cleanup |
| `app/config.py`                                  | Новые настройки: timeouts, approval mode               |
| `app/services/llm.py`                            | Timeout в клиенте, тайминги в логах                    |
| `app/services/pipeline.py`                       | `mark_step_running()`, heartbeat, context size warning |
| `app/models/project.py`                          | Поле `generation_started_at`                           |
| `app/workers/celery_app.py`                      | Soft time limit, частота cleanup                       |
| `app/api/projects.py`                            | Endpoint `/approve-page`, поле в response              |
| `frontend/src/pages/ProjectDetailPage.tsx`       | Таймер, кнопка approval                                |
| `frontend/src/components/tasks/StepCard.tsx`     | Live-таймер для running шагов                          |
| `frontend/src/api/projects.ts`                   | Метод `approvePage()`                                  |
| `frontend/src/components/common/StatusBadge.tsx` | Новый статус                                           |
| Alembic migration                                | `generation_started_at` колонка                        |
