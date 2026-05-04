# Май 2026 — task53: черновики проектов (Add Project modal)

## Контекст

Модалка создания проекта поддерживала только полный сценарий «Start Project» (валидация → `pending` → Celery). Нужны промежуточные сохранения формы, список черновиков с фильтром и запуск готового проекта отдельной кнопкой.

## Решение (кратко)

- Статус **`draft`** (строка в колонке **`status`**, без enum-миграции).
- Nullable поля и **`target_site`** на **`site_projects`** (миграция **`z2a3b4c5d6e7`**).
- Эндпоинты **`POST /api/projects/draft`**, **`PATCH /api/projects/{id}`**, **`POST /api/projects/{id}/launch`**.
- UI: **Save Draft**, **Launch Project**, бейдж, фильтр, клик по строке черновика.

## Backend

| Область | Изменения |
|--------|-----------|
| `alembic/versions/z2a3b4c5d6e7_site_projects_draft_nullable.py` | Nullable `blueprint_id`, `site_id`, `seed_keyword`, `country`, `language`; колонка `target_site` (String 500). |
| `app/models/project.py` | Соответствие модели; комментарий к `status` дополнен `\| draft`. |
| `app/schemas/project.py` | `SiteProjectDraftCreate`, `SiteProjectUpdate`; в `SiteProjectResponse` опциональны `blueprint_id`, `site_id`, `seed_keyword`. |
| `app/api/projects.py` | Три новых хендлера; duplicate `not_in(["failed", "draft"])` в create и clone; `GET /projects` отдаёт `author_id`, `project_keywords`, `legal_template_map`, `target_site`; детали проекта и `blueprint_page_count` при отсутствии blueprint; clone без `site_id` у источника → 400 без `target_site` в теле. |

## Frontend

| Файл | Изменения |
|------|-----------|
| `frontend/src/api/projects.ts` | `saveDraft`, `updateDraft`, `launchDraft`, типы payload. |
| `frontend/src/types/project.ts` | Статус `draft`, опциональные поля, `target_site`. |
| `frontend/src/pages/ProjectsPage.tsx` | Режим модалки `edit-draft`, мутации, валидация launch, футер, фильтр, `onRowClick`. |
| `frontend/src/components/common/StatusBadge.tsx` | Ветка `draft`. |
| `frontend/src/pages/ProjectDetailPage.tsx` | Редирект со страницы черновика; безопасный вывод nullable полей. |

## Проверка

- `alembic upgrade head` на dev-БД.
- Сценарии из `task53.md` (сохранение имени, дозаполнение, launch, duplicate при launch, удаление черновика, 503 worker при launch — статус остаётся `draft` до первого успешного commit смены статуса).
