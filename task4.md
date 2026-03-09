## 1. КРИТИЧЕСКИЕ БАГИ И ПРОБЛЕМЫ

**1.1. Опечатка-дубликат в pipeline.py**

В `run_pipeline` есть строка `outline_data["fiinal_structure"] = outline_json_str` (два "i" в "fiinal"). Это бессмысленный дубль поля `final_structure`. Нужно удалить.

**1.2. Утечка DB-сессии в Celery worker**

В `process_generation_task` есть `db.close()` внутри блока `except`, но если `run_pipeline` завершается успешно — сессия никогда не закрывается. Нужно перенести `db.close()` в блок `finally`. Сейчас код выглядит так:

```python
except Exception as exc:
    pass
    db.close()  # это ВНУТРИ except, не в finally
```

Правильно — `try/except/finally` с `db.close()` в `finally`, как уже сделано в `process_site_project`.

**1.3. CORS allow_origins=["*"] в продакшене**

В `main.py` стоит `allow_origins=["*"]`. Для продакшена это уязвимость. Нужно брать список допустимых origins из `.env` (например, `CORS_ORIGINS=https://admin.yourdomain.com`).

---

## 2. АРХИТЕКТУРА PIPELINE

**2.1. Монолитная функция run_pipeline (~400 строк)**

Вся логика 13 фаз живёт в одной функции. Рекомендация: разбить на отдельные функции-фазы и оркестратор:

```python
def run_pipeline(db, task_id):
    ctx = PipelineContext(db, task)
    phase_serp(ctx)
    phase_scraping(ctx)
    phase_analysis(ctx)
    phase_generation(ctx)
    # ...
```

Каждая фаза — отдельная функция в том же файле или в `pipeline/phases/`. Это даст возможность тестировать фазы изолированно и перезапускать с конкретной фазы (resume).

**2.2. Нет механизма возобновления (resume) с точки падения**

Сейчас если pipeline упал на Phase 8 из 13, при retry всё начинается сначала (с SERP). Нужно: проверять `step_results` при старте и пропускать уже выполненные фазы. Данные уже сохраняются через `save_step_result` — осталось добавить логику проверки.

**2.3. Избыточные `db.commit()` — по 2-3 коммита на каждый шаг**

Каждый вызов `add_log` и `save_step_result` делает отдельный `db.commit()`. При 13 фазах это 50+ коммитов на задачу. Рекомендация: батчить — один коммит после каждой фазы целиком, а не после каждого лог-сообщения.

---

## 3. КАЧЕСТВО КОДА И НАДЁЖНОСТЬ

**3.1. LLM-клиент создаётся при каждом вызове**

В `llm.py` функция `generate_text` вызывает `get_openai_client()` каждый раз. OpenAI-клиент можно инстанцировать один раз как модульную переменную.

**3.2. Scraper использует синхронные requests**

`scraper.py` делает `requests.get()` последовательно для 10 URL. При таймауте 15 сек на каждый, worst case — 150 секунд. Рекомендация: использовать `concurrent.futures.ThreadPoolExecutor` или `aiohttp` для параллельного скрейпинга. Это ускорит Phase 2 в 3-5 раз.

**3.3. Нет валидации JSON-ответов от LLM**

В нескольких местах вызывается `json.loads()` на ответ LLM. Если модель вернёт невалидный JSON (markdown-обёртка, комментарий), pipeline упадёт. Нужна обёртка-парсер, которая очищает ответ: убирает ```json-фенсинг, пытается извлечь JSON из текста.

**3.4. Хардкод строк-ключей для шагов**

Названия шагов типа `"ai_structure_analysis"`, `"chunk_cluster_analysis"` разбросаны по всему pipeline как строковые литералы. Лучше вынести в Enum или константы, чтобы опечатки ловились на этапе разработки.

---

## 4. БЕЗОПАСНОСТЬ

**4.1. API без аутентификации**

Все эндпоинты открыты. Любой, кто знает URL, может создавать задачи, читать статьи, менять настройки. Минимум — добавить API-ключ через Header (`X-API-Key`) или Bearer token. Идеально — JWT с ролями.

**4.2. Settings API отдаёт API-ключи в открытом виде**

`GET /api/settings` возвращает `OPENROUTER_API_KEY`, `DATAFORSEO_PASSWORD` и т.д. Нужно маскировать: `"sk-or-...****1234"`.

**4.3. Нет rate-limiting на API**

Нет защиты от перегрузки. Кто-то может послать 1000 задач через `POST /api/tasks/bulk`. Рекомендация: `slowapi` или middleware с лимитами.

---

## 5. DATABASE & ORM

**5.1. Нет индексов на часто запрашиваемые поля**

`Task.status`, `Task.project_id`, `Task.target_site_id`, `Prompt.agent_name + is_active` — по ним идут фильтры на каждом запросе. Нужно добавить индексы через Alembic-миграцию.

**5.2. JSONB поля без структуры**

`task.step_results`, `task.logs`, `task.outline`, `task.serp_data` — всё JSONB без schema. Со временем это станет проблемой для отладки. Рекомендация: хотя бы Pydantic-модели для валидации при записи/чтении, даже если в БД остаётся JSONB.

**5.3. Мутация JSONB через dict(task.step_results)**

SQLAlchemy не отслеживает изменения внутри JSONB. Текущий workaround (`updated = dict(task.step_results); task.step_results = updated`) работает, но хрупок. Лучше использовать `flag_modified(task, "step_results")` из `sqlalchemy.orm.attributes` — это чище и надёжнее.

---

## 6. CELERY & WORKERS

**6.1. Нет Celery Beat для периодических задач**

По ТЗ есть дашборд со статистикой, но нет cleanup-задач: удаление старых логов, очистка зависших `processing`-задач (если worker упал), агрегация метрик. Нужен `celery beat` + расписание.

**6.2. process_site_project запускает pipeline синхронно**

Все страницы проекта генерируются последовательно в одном Celery-воркере. Если проект содержит 20 страниц — один worker заблокирован на несколько часов. Рекомендация: запускать каждую страницу как отдельную sub-task через `chord`/`chain`, чтобы Celery мог распределить нагрузку.

**6.3. task_time_limit=900 может быть мало**

15 минут на задачу при 13 LLM-вызовах (каждый с retry до 3 раз, с backoff до 300 секунд для rate limit) — может не хватить. Нужно либо увеличить лимит, либо вынести LLM-retry из синхронного sleep в Celery retry.

---

## 7. FRONTEND (STREAMLIT)

**7.1. Вкладка «Сайты» — заглушка**

`st.info("Раздел 'Сайты' в разработке.")` — при том, что API для sites уже полностью реализован. Нужно доделать.

**7.2. Polling через time.sleep(5) + st.rerun()**

На вкладке задач, при `status == "processing"`, стоит `time.sleep(5)` внутри рендера. Это блокирует весь Streamlit-процесс. Лучше использовать `st.fragment` с `run_every` (Streamlit 1.33+) или перейти на WebSocket-подход.

**7.3. Нет пагинации**

Все списки (задачи, статьи, проекты) загружают до 50 записей. При масштабировании нужна полноценная пагинация с offset/cursor в UI.

---

## 8. ТЕСТИРОВАНИЕ

**8.1. Тестов нет вообще**

В ТЗ упомянуты `tests/test_pipeline.py` и `tests/test_api.py`, но в проекте их нет. Минимальный набор: unit-тесты на `call_agent`, `apply_template_vars`, `parse_html`, интеграционные тесты на API-эндпоинты с тестовой БД.

---

## 9. DEVOPS & ИНФРАСТРУКТУРА

**9.1. Нет healthcheck в docker-compose**

Ни один сервис не имеет healthcheck. Если FastAPI стартует, но не может подключиться к БД — docker-compose не узнает. Нужно добавить healthcheck для web, worker, redis.

**9.2. Все 4 сервиса используют один Dockerfile**

`web`, `worker`, `frontend` — все собираются из одного образа. Frontend не нуждается в Celery-зависимостях, а worker не нуждается в Streamlit. Рекомендация: multi-stage build или отдельные Dockerfile для уменьшения размера образов.

**9.3. Нет Nginx в docker-compose**

В ТЗ упомянут Nginx reverse proxy + SSL, но его нет в compose. Для продакшена нужен.

---

## 10. ПРИОРИТЕТЫ ДЛЯ ANTIGRAVITY

Я бы рекомендовал такой порядок работы:

**Фаза A — Critical Fixes (1 день):** пункты 1.1-1.4, 4.1 (API auth), 6.2 (db.close в finally).

**Фаза B — Pipeline Resilience (2-3 дня):** resume с точки падения (2.2), JSON-парсер для LLM (3.3), параллельный скрейпинг (3.2), разбиение pipeline на фазы (2.1).

**Фаза C — Security & Production (1-2 дня):** CORS из env (1.3), маскировка ключей (4.2), индексы в БД (5.1), healthcheck (9.1).

**Фаза D — Quality of Life (2-3 дня):** тесты (8.1), доделать вкладку Сайты (7.1), пагинация (7.3), Celery Beat (6.1).

Хочешь, чтобы я оформил какой-то из этих блоков как полноценное ТЗ для antigravity с конкретными файлами, кодом и acceptance criteria?