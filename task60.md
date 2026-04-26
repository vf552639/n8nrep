# Аудит проекта: слабые места и приоритеты исправлений

## Контекст

Проект — backend на FastAPI + Celery + PostgreSQL и frontend на Vite/React для генерации SEO-контента через LLM. Запрошен анализ кода и список слабых мест с приоритетом, что чинить в первую очередь. Этот документ — punch list находок, отсортированный от блокирующих до косметических. Каждая позиция верифицирована чтением кода (а не пересказом).

Все пути относительны корня воркtree: `/Users/andrey/Documents/Python/n8nrep/.claude/worktrees/busy-khorana-bdd05f/`.

---

## 🔴 CRITICAL — чинить немедленно

### 1. Auth выключается при пустом `API_KEY`
- **Где:** [app/api/deps.py:6-9](app/api/deps.py)
  ```python
  if not settings.API_KEY:
      return  # auth полностью отключается
  ```
- **Проблема:** в [app/config.py:17](app/config.py) `API_KEY: str = ""` по умолчанию. Если в проде забыли проставить переменную — API открыт всему миру. CI намеренно ставит `API_KEY=""` ([.github/workflows/ci.yml:46](.github/workflows/ci.yml)) — значит, эта ветка реально работает.
- **Фикс:** сделать `API_KEY` обязательным полем (без default) или добавить явный `AUTH_DISABLED: bool = False`, по умолчанию `False`, и логировать WARNING при старте если auth выключен.

### 2. CORS `*` + `allow_credentials=True`
- **Где:** [app/main.py:90-99](app/main.py)
  ```python
  origins = [...] if settings.CORS_ORIGINS else ["*"]
  app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, ...)
  ```
- **Проблема:** при пустом `CORS_ORIGINS` ставится `["*"]`. Браузеры отвергают `*` с credentials, но Starlette в этом случае эхом возвращает Origin запроса — фактически это «разрешить всем». Дефолт `CORS_ORIGINS="*"` в [app/config.py:18](app/config.py) усугубляет.
- **Фикс:** валидировать `CORS_ORIGINS` при старте: если `*` — отключать `allow_credentials`. По умолчанию — пустой список и явный fail.

### 3. SSRF в `/api/tasks/fetch-url-meta`
- **Где:** [app/api/tasks.py:43-50](app/api/tasks.py) → [app/services/scraper.py:118](app/services/scraper.py)
- **Проблема:** эндпоинт принимает любой URL и `requests.get` на него уходит без блокировки приватных сетей. Атакующий с валидным API-ключом (или вообще без, см. #1) делает запросы к `169.254.169.254`, `localhost`, внутренним сервисам. Дополнительно `timeout=12` × долгое подключение = удерживает воркер.
- **Фикс:** валидировать host: резолвить DNS → отбрасывать приватные/loopback диапазоны (`ipaddress.ip_address().is_private/is_loopback/is_link_local`); запретить `file://`, нестандартные порты; уменьшить timeout до 5–8 сек.

### 4. Bulk CSV upload без лимита размера и валидации
- **Где:** [app/api/tasks.py:303-340](app/api/tasks.py)
  ```python
  contents = await file.read()  # читает весь файл в память
  ```
- **Проблема:** нет лимита размера, типа, числа строк. 1 ГБ CSV → OOM воркера. Также `row["keyword"]`/`row["country"]`/`row["language"]` падают `KeyError` если колонки отсутствуют — попадает в общий `except`, рассылка в `errors`, но шум в логах.
- **Фикс:** проверить `file.content_type`, ограничить через `Content-Length` (например, 1 МБ), валидировать заголовки CSV до цикла; ограничить число строк (например, 500).

---

## 🟠 HIGH — чинить в ближайшее время

### 5. Нет авторизации/изоляции владельца (IDOR)
- **Где:** все хендлеры в [app/api/tasks.py:93](app/api/tasks.py), [app/api/projects.py](app/api/projects.py), [app/api/sites.py](app/api/sites.py) и т. д.
- **Проблема:** единственная защита — общий `verify_api_key`. Любой обладатель ключа видит и редактирует чужие задачи/проекты/сайты. Если планируется multi-tenant — баг; если single-tenant — допустимо, но нужно явно зафиксировать в README.
- **Фикс (если multi-tenant):** ввести `User`/`Tenant`, добавить `owner_id` к моделям, фильтровать запросы; либо явно задокументировать однопользовательский режим.

### 6. `print()` логирует параметры LLM-запросов в stdout
- **Где:** [app/services/llm.py:86](app/services/llm.py) и далее
- **Проблема:** имя модели, токены, размеры в stdout — попадает в логи без структуры. Не утечка ключа, но шум, перемешанный со структурным логированием в `app/logging_config.py`.
- **Фикс:** заменить на `logger.debug(...)` через `logging.getLogger(__name__)`.

### 7. SSRF в `image_hosting.upload_from_url`
- **Где:** [app/services/image_hosting.py](app/services/image_hosting.py) — `upload_from_url(image_url)` через `requests.get(url, timeout=60)`
- **Проблема:** тот же класс уязвимости, что #3, плюс крайне большой timeout 60 сек. Если URL приходит из пользовательского ввода (через approve-images), атакующий может сканировать внутреннюю сеть.
- **Фикс:** общий хелпер `safe_http_get` с проверкой private IP + ограничение Content-Type на `image/*` + timeout 10 сек + лимит размера ответа.

### 8. Контейнеры запускаются от root
- **Где:** [Dockerfile](Dockerfile), [frontend/Dockerfile](frontend/Dockerfile)
- **Проблема:** нет `USER` директивы — `uvicorn` идёт от root. При компрометации процесса — root в контейнере.
- **Фикс:** `RUN useradd -m -u 1000 app && chown -R app /app` + `USER app` перед `CMD`.

### 9. CI не проверяет lint/build фронта на типы и стиль
- **Где:** [.github/workflows/ci.yml:50-62](.github/workflows/ci.yml)
- **Проблема:** только `npm run build`. Нет `npm run lint`, нет `tsc --noEmit`. ESLint в [frontend/.eslintrc.cjs:17](frontend/.eslintrc.cjs) выключает `no-explicit-any` — глобальная амнистия для `any`.
- **Фикс:** добавить в CI шаг `npm run lint` и `tsc --noEmit`. Перевести `no-explicit-any` в `warn` (фиксить инкрементально).

### 10. `pool_timeout=30` блокирует event loop
- **Где:** [app/database.py:16](app/database.py)
- **Проблема:** FastAPI хендлеры синхронные, `Depends(get_db)` — sync. Под нагрузкой все 10 коннектов заняты → каждый запрос ждёт до 30 сек, блокируя поток.
- **Фикс:** уменьшить до 5–10 сек, увеличить `pool_size` или `max_overflow` если нужна большая пропускная способность.

### 11. Нет security-сканирования зависимостей в CI
- **Где:** [.github/workflows/ci.yml](.github/workflows/ci.yml)
- **Проблема:** ни `pip-audit`, ни `bandit`, ни `npm audit` не запускаются. Уязвимости в зависимостях остаются незамеченными.
- **Фикс:** добавить шаг `pip-audit --strict` (требует pinned reqs) и `npm audit --omit=dev` для фронта.

---

## 🟡 MEDIUM — план на спринт

### 12. Хардкод fallback `http://localhost:8000/api` в нескольких местах фронта
- **Где:** [frontend/src/api/client.ts:7](frontend/src/api/client.ts) + ещё в нескольких файлах (см. `SerpStepView.tsx`)
- **Фикс:** один централизованный `apiBaseUrl` в `frontend/src/config.ts`; в продакшен-сборке падать при отсутствии `VITE_API_URL`.

### 13. API-ключ хранится в `localStorage`
- **Где:** [frontend/src/api/client.ts:15](frontend/src/api/client.ts)
- **Фикс:** для long-term — переход на куку HttpOnly + Secure. Минимум — задокументировать что ключ виден любым XSS.

### 14. Отсутствие rate limiting
- **Где:** все публичные эндпоинты, особенно `/api/tasks/fetch-url-meta`, `/api/tasks/bulk`, `/api/health`.
- **Фикс:** подключить `slowapi` с per-IP/per-API-key buckets.

### 15. Корневые dev-файлы в git
- **Где:** [task54.md](task54.md), [image_prompt_extractor.py](image_prompt_extractor.py), [update_prompt.py](update_prompt.py) в корне репо
- **Фикс:** перенести в `docs/` или удалить если устарели; добавить convention в `.gitignore`.

### 16. Нет фронтовых тестов
- **Где:** [.github/workflows/ci.yml](.github/workflows/ci.yml) frontend job
- **Фикс:** vitest + React Testing Library, минимум smoke-тесты на ключевые страницы (TasksPage, ProjectDetailPage).

### 17. Нет security-заголовков
- **Где:** [app/main.py](app/main.py)
- **Фикс:** middleware с `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, базовый CSP для HTML preview-эндпоинтов.

### 18. Hardcoded `HTTP-Referer: https://example.com` в LLM-запросах
- **Где:** [app/services/llm.py:104](app/services/llm.py)
- **Фикс:** вынести в конфиг (OpenRouter использует это для отчётности).

### 19. Telegram chat_id в `.env.example`
- **Где:** [.env.example:38](.env.example) `TELEGRAM_CHAT_ID=-1003841650237`
- **Проблема:** похоже на реальный chat_id — мелкая утечка. Если это «чужой» чат — отправители могут флудить туда при misconfiguration.
- **Фикс:** заменить на `-100XXXXXXXXX`.

### 20. Нет idempotency на retry Celery-задач
- **Где:** [app/workers/tasks.py:94](app/workers/tasks.py) (`process_generation_task` с `max_retries=3`)
- **Фикс:** перед началом шага проверять статус таски; если уже в `running` от другого worker — fail-fast.

---

## 🟢 LOW — backlog

- **21.** ESLint правило `no-unused-vars` в режиме `warn` — в CI должно быть `error` ([frontend/.eslintrc.cjs:18](frontend/.eslintrc.cjs)).
- **22.** Pre-commit hook не запускает eslint для фронта ([.pre-commit-config.yaml](.pre-commit-config.yaml)).
- **23.** Нет ARIA-атрибутов на кликабельных `div`, мало `alt=` (по результатам сканирования). Подключить `eslint-plugin-jsx-a11y`.
- **24.** Coverage threshold = 55% — низковато; постепенно поднимать к 75%.
- **25.** `expire_on_commit=False` глобально ([app/database.py:30](app/database.py)) — оправдано task59, но стоит документировать риск stale ORM в комментарии в самом коде (сейчас комментарий есть — ок, но стоит ссылаться в `db_session()`).

---

## Что делать первым (concrete next steps)

Если идти по приоритетам, минимальный набор фиксов на **один PR** перед prod-выкаткой:

1. Сделать `API_KEY` обязательным или ввести явный флаг `AUTH_DISABLED` (#1).
2. Запретить `CORS_ORIGINS=*` вместе с `allow_credentials=True` (#2).
3. Добавить SSRF-валидацию URL в `fetch_url_meta` и `image_hosting.upload_from_url` (#3, #7).
4. Лимит размера и числа строк для `/tasks/bulk` (#4).
5. `USER appuser` в обоих Dockerfile (#8).
6. Включить `npm run lint` + `tsc --noEmit` в CI (#9).

Это закрывает все Critical и три самых дешёвых High. Остальные High/Medium — отдельными PR-ами.

---

## Verification

Каждый фикс из приоритетных проверяется так:

- **#1 / #2:** запустить локально с пустым `API_KEY` и `CORS_ORIGINS=*` — приложение должно отказаться стартовать или явно WARNING+restrict.
- **#3 / #7:** `curl -X POST .../fetch-url-meta -d '{"url":"http://169.254.169.254"}'` → 400.
- **#4:** `curl -X POST .../tasks/bulk -F "file=@/dev/zero"` (truncate до >MAX) → 413.
- **#8:** `docker run ... id` → `uid=1000(app)`.
- **#9:** PR с заведомо «грязным» TS должен фейлить CI.

---

## Файлы, которые точно затронут фиксы (Critical/High)

- [app/api/deps.py](app/api/deps.py) — auth-логика
- [app/config.py](app/config.py) — обязательные поля и валидация
- [app/main.py](app/main.py) — CORS, security headers, lifespan-проверки
- [app/api/tasks.py](app/api/tasks.py) — bulk upload, fetch-url-meta
- [app/services/scraper.py](app/services/scraper.py) — SSRF guard
- [app/services/image_hosting.py](app/services/image_hosting.py) — SSRF guard для image URL
- [app/services/llm.py](app/services/llm.py) — заменить `print` на `logger`
- [app/database.py](app/database.py) — `pool_timeout`
- [Dockerfile](Dockerfile), [frontend/Dockerfile](frontend/Dockerfile) — non-root user
- [.github/workflows/ci.yml](.github/workflows/ci.yml) — lint frontend, security scan
- [frontend/.eslintrc.cjs](frontend/.eslintrc.cjs) — `no-explicit-any` → warn
- [frontend/src/api/client.ts](frontend/src/api/client.ts) + соседние api/* — централизация baseURL
