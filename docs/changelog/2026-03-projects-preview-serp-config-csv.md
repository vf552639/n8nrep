# Март 2026 — Проекты: preview (dry-run), SERP-конфиг, CSV, health-check SERP

**Дата:** 2026-03-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Цель:** планировать запуск без записи в БД, задавать SERP на уровне проекта, выгружать отчёты и видеть состояние SERP API до старта.

**Backend (`app/api/projects.py`, `app/services/serp.py`, `app/api/health.py`, `app/models/project.py`)**

- **`POST /api/projects/preview`** — регистрируется **перед** `POST /api/projects/`, чтобы путь не перехватывался как `{id}`. Тело: как создание проекта без обязательного `name` (см. **`ProjectPreviewRequest`**): blueprint, seed, GEO, `target_site`, опционально **`author_id`**, **`serp_config`**. Резолв сайта **без автосоздания** (если сайт не найден — в ответе `site.will_be_created`, предупреждение в **`warnings`**). Автор: manual / auto / none. Проверка наличия **HTML-шаблона** у сайта: **`site.template_id`** и активная запись **`Template`**. Страницы блупринта с итоговыми keyword и **standard/brand** шаблоном. **Оценка стоимости:** средняя по последним **50** завершённым задачам с `total_cost > 0`, умноженная на число страниц; при отсутствии данных — `null`. В ответе: **`serp_health`** (`get_serp_health()`), дополнительные **`warnings`** при `overall != ok` для SERP.
- **`SiteProject.serp_config`** (JSONB): ключи `search_engine`, `depth`, `device`, `os` — валидация при **`POST /api/projects`**. Сохраняется в проект; при создании задач в **`process_site_project`** в **`Task.serp_config`** подставляется конфиг проекта. В **`GET /api/projects`** и **`GET /api/projects/{id}`** поле **`serp_config`** в ответе. Клонирование копирует **`serp_config`** с исходного проекта.
- **`POST /api/projects`** — в ответе опционально **`serp_warning`** (мягкая проверка `get_serp_health()` после постановки в очередь; создание не блокируется).
- **`GET /api/projects/{id}/export-csv`** — CSV по задачам проекта (колонки: page_slug, keyword, page_type, status, filename, title, description, word_count, cost, fact_check, created_at), пакетная загрузка **`GeneratedArticle`** и **`BlueprintPage`**, строка **TOTAL** в конце.
- **`GET /api/health/serp`** — обёртка над **`get_serp_health()`** в `serp.py`: тестовые вызовы DataForSEO и SerpAPI, поля **`overall`**, **`_from_cache`**, TTL **5 минут**, параметр **`?force=true`** для сброса кэша.

**Frontend (`ProjectsPage.tsx`, `ProjectDetailPage.tsx`, `DashboardPage.tsx`, `frontend/src/api/projects.ts`, `frontend/src/api/dashboard.ts`)**

- Модалка создания проекта: кнопка **Preview** (иконка Eye), блок превью (карточки, таблица страниц, warnings), секция **Advanced SERP Settings** (engine, depth, device, os); при создании — toast с **`serp_warning`** при наличии.
- Список проектов: колонка **Cost**; деталка: **`Export Summary (CSV)`** (blob, авторизация через axios), бейджи нестандартного **serp_config** в шапке.
- **Dashboard:** бейдж состояния SERP (online / degraded / not configured), опрос раз в **5 минут**.

- **`POST /api/projects/{id}/clone`** — копия проекта в статусе **`pending`** (новые задачи, без статей); опционально переопределить имя, seed, GEO, сайт, автора; **`serp_config`** копируется с исходника.
- **`POST /api/projects/{id}/start`** — только для статуса **`pending`**: постановка **`process_site_project`** в очередь (проверка worker **503** при недоступности). Дубликат здесь **не** проверяется; **409** с **`existing_project_id`** — при **`POST /api/projects`** и **`POST .../clone`**, если уже есть неархивный проект с тем же **blueprint + seed + site** и статусом не **`failed`**.
- **`GET /api/projects`** / **`GET /api/projects/{id}`** — агрегаты **`total_cost`**, **`started_at`**, **`completed_at`**, **`duration_seconds`**, **`avg_cost_per_page`**, **`avg_seconds_per_page`**, **`remaining_pages`**, **`log_events`** (массив записей проекта); в списке — **`total_cost`** по сумме задач.
- **`app/services/serp.py`:** при ошибке обоих провайдеров SERP — **retry** с экспоненциальной задержкой (по умолчанию Google organic path).

**Миграции Alembic**

- **`f1a2b3c4d5e7_add_project_timings_and_logs.py`** — **`started_at`**, **`completed_at`**, колонка **`logs`** у **`site_projects`** (переименована в **`log_events`**, миграция **`t7u8v9w0x1yb`**).
- **`g2b3c4d5e6f8_add_serp_config_to_site_projects.py`** — **`serp_config`** у **`site_projects`**; см. также **`c8f9a0b1d2e3_add_serp_config_to_tasks.py`** — **`serp_config`** у **`tasks`**.

---
