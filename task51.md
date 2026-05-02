# Диагноз и фикс egress в Supabase-проекте «DB Authors»

## Context

В Supabase-проекте `DB Authors` egress 10.19 / 5 ГБ (204%), хотя сама БД — всего 47 МБ, а Storage — 0. Значит, проблема не в размере данных, а в том, что одни и те же строки тянутся через API/PostgREST/SQL очень часто. Цель плана — устранить главные источники повторяющегося трафика, чтобы укладываться в free-tier (5 ГБ) без апгрейда.

## Корневые причины (по убыванию вклада)

### 1. `/api/authors` отдаёт всю таблицу целиком, фронт дёргает её на каждой странице

[app/api/authors.py:28-58](app/api/authors.py:28) — `GET /` делает `db.query(Author).all()` без лимита и без выбора колонок. Возвращает все 14 полей, включая «жирные» Text-колонки `bio`, `target_audience`, `rhythms_style`, `exclude_words`, `imitation`, `face` (могут быть по несколько КБ каждое).

Фронт подписан на этот эндпоинт через React Query из **пяти** мест с одинаковым `queryKey: ["authors"]`, но **без `staleTime`** (т.е. дефолт = 0 → стаёт устаревшим мгновенно):

- [frontend/src/pages/AuthorsPage.tsx:245](frontend/src/pages/AuthorsPage.tsx:245) — `getAll({ limit: 1000 })`
- [frontend/src/pages/ProjectsPage.tsx:585](frontend/src/pages/ProjectsPage.tsx:585)
- [frontend/src/pages/ProjectDetailPage.tsx:821](frontend/src/pages/ProjectDetailPage.tsx:821)
- [frontend/src/pages/SitesPage.tsx:223](frontend/src/pages/SitesPage.tsx:223)
- [frontend/src/pages/TasksPage.tsx:386](frontend/src/pages/TasksPage.tsx:386)

Каждое монтирование страницы и каждый refocus окна → новая загрузка всей таблицы со всеми текстовыми полями. При 100–200 авторов с тяжёлыми био это легко даёт 1–5 МБ за запрос; пара тысяч переходов/refocus в месяц — и 10 ГБ набегает.

### 2. N+1 на `authors` в пайплайне генерации страниц

[app/services/pipeline/assembly.py:121-131](app/services/pipeline/assembly.py:121) — `_apply_author_footer` делает отдельный `SELECT * FROM authors WHERE id = ?` **на каждую сгенерированную страницу**. При прогоне сайта на сотни страниц это сотни одинаковых запросов с полным набором Text-колонок. Добавлено недавно вместе с `feat(blueprints): add per-page author geo footer toggle` (f4ff8d8).

### 3. Периодические тяжёлые запросы воркера

[app/workers/tasks.py](app/workers/tasks.py) — `cleanup_stale_tasks` каждые 10 минут делает `db.query(Task).filter(...).all()` и `add_log()` по каждой записи. Сам по себе вклад умеренный, но усугубляет общую картину.

### 4. Bulk-export эндпоинты

CSV/ZIP экспорт проектов ([app/api/projects.py:687](app/api/projects.py:687), [:1221](app/api/projects.py:1221)) тянет все таски/статьи без выбора колонок. После `task60` это под auth, но если им регулярно пользуются — тоже значимый источник.

## Рекомендуемый фикс (минимальный)

Все правки — read-side, без миграций.

### A. Сделать `/api/authors` лёгким и пагинируемым ([app/api/authors.py:28](app/api/authors.py:28))

- Добавить параметры `limit` (дефолт 100, макс 500) и `offset`.
- По умолчанию отдавать «лёгкий» набор полей: `id, author, country, country_full, language, year, usage_count`. Тяжёлые Text-поля (`bio`, `target_audience`, `rhythms_style`, `exclude_words`, `imitation`, `face`) — только если `?full=1`.
- В SQL заменить `db.query(Author)` на `db.query(Author.id, Author.author, …)` чтобы PostgREST/SQLAlchemy не тащил Text-колонки с диска.

### B. Перестать рефетчить авторов на каждый чих фронта

Во всех пяти `useQuery({ queryKey: ["authors"] … })` добавить:

```ts
staleTime: 5 * 60 * 1000,       // 5 минут
refetchOnWindowFocus: false,
```

Файлы: [AuthorsPage.tsx:245](frontend/src/pages/AuthorsPage.tsx:245), [ProjectsPage.tsx:585](frontend/src/pages/ProjectsPage.tsx:585), [ProjectDetailPage.tsx:821](frontend/src/pages/ProjectDetailPage.tsx:821), [SitesPage.tsx:223](frontend/src/pages/SitesPage.tsx:223), [TasksPage.tsx:386](frontend/src/pages/TasksPage.tsx:386).

Альтернатива — выставить эти дефолты глобально в `QueryClient` в корне приложения, чтобы не править пять мест.

В `ProjectsPage`/`SitesPage`/`TasksPage`/`ProjectDetailPage` авторы нужны только для дропдауна — там вообще можно ходить в `getAll({ light: true })` и не тянуть `bio`/`target_audience`/etc.

### C. Убрать N+1 в пайплайне ([app/services/pipeline/assembly.py:121](app/services/pipeline/assembly.py:121))

Подгрузить автора один раз на запуск пайплайна и сохранить в `PipelineContext` (или использовать `joinedload(Task.author)` при загрузке таска). Тогда `_apply_author_footer` будет читать из памяти.

### D. (Опционально) Закэшировать ответ `/api/authors`

Авторы меняются редко. Можно держать in-process LRU/TTL-кэш на 60 сек в FastAPI-эндпоинте и инвалидировать его в `create_author` / `update_author` / `delete_author`. Это убьёт остаточный egress даже при отключённом фронт-кэше.

## Критичные файлы

- [app/api/authors.py](app/api/authors.py) — A, D
- [app/services/pipeline/assembly.py](app/services/pipeline/assembly.py) — C
- [frontend/src/pages/AuthorsPage.tsx](frontend/src/pages/AuthorsPage.tsx) — B
- [frontend/src/pages/ProjectsPage.tsx](frontend/src/pages/ProjectsPage.tsx) — B
- [frontend/src/pages/ProjectDetailPage.tsx](frontend/src/pages/ProjectDetailPage.tsx) — B
- [frontend/src/pages/SitesPage.tsx](frontend/src/pages/SitesPage.tsx) — B
- [frontend/src/pages/TasksPage.tsx](frontend/src/pages/TasksPage.tsx) — B
- [frontend/src/api/authors.ts](frontend/src/api/authors.ts) — добавить параметры `limit`/`light`

## Верификация

1. **Размер ответа**: `curl -s -H "Authorization: …" http://localhost:8000/api/authors/ | wc -c` до и после правки A — ожидаемое падение в 5–20× за счёт light-режима.
2. **Частота запросов**: открыть DevTools → Network, перейти Projects → Sites → Tasks → Authors и обратно. До: на каждую вкладку новый запрос к `/api/authors`. После: один запрос, остальные из кэша React Query.
3. **Пайплайн**: запустить генерацию сайта на ≥10 страниц, посмотреть в логах SQL (или включить `echo=True` в SQLAlchemy) — должен быть один `SELECT … FROM authors WHERE id=…`, а не один на страницу.
4. **Egress в Supabase**: через 24 часа после деплоя проверить дашборд проекта — суточный egress должен упасть в разы.
