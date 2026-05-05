# Май 2026 — task58: per-page competitor URLs + `search_engine=off`

## Контекст

Для многостраничных проектов (например, slots) project-wide `competitor_urls` было недостаточно: нужен отдельный список URL конкурентов для каждой страницы blueprint после кластеризации. Параллельно требовался режим полного отключения DataForSEO/SERP-fetch на проект.

## Что изменено

- **Backend validation (`app/api/projects.py`)**
  - `_validate_serp_config` теперь принимает `search_engine="off"` вместе с существующими `google|bing|google+bing`.

- **Pipeline (`app/services/pipeline/steps/serp_step.py`)**
  - `SerpStep` читает per-page URLs из `project.project_keywords.clustered[page_slug].competitor_urls`.
  - Если per-page URLs не заданы, используется fallback на `project.competitor_urls`.
  - При `search_engine="off"`:
    - `fetch_serp_data()` не вызывается;
    - `task.serp_data` формируется только из пользовательских URL (`source: user_only`);
    - пишется warning, если пользовательские URL отсутствуют.
  - При обычных engine сохранено старое поведение fetch+merge, но с приоритетом per-page URLs над project-wide.

- **Frontend (`frontend/src/pages/ProjectsPage.tsx`)**
  - В advanced SERP добавлена опция `Off (skip DataForSEO)`.
  - В `formData` добавлен `page_competitor_urls_raw: Record<string, string>`.
  - В `Keyword Distribution Preview` под каждой карточкой страницы добавлен textarea `Competitor URLs`.
  - В `assembleExtras()` per-page URLs сохраняются в `project_keywords.clustered[slug].competitor_urls`.
  - В режиме `edit-draft` per-page URLs восстанавливаются обратно в textarea.

- **Типы (`frontend/src/api/projects.ts`, `frontend/src/types/project.ts`)**
  - расширен union для `search_engine` значением `"off"`;
  - тип clustered-элемента дополнен `competitor_urls?: string[]`.

## Тесты

- Добавлен `tests/api/test_projects_serp_engine_off.py` (валидация `search_engine="off"` и reject неизвестного engine).
- Добавлен `tests/services/test_serp_step_per_page_urls.py`:
  - `off` использует только per-page URL;
  - `off` делает fallback на project-wide URL;
  - `google` мержит per-page URL и не берет project-wide при наличии per-page.

## Примечания по верификации

- Unit-тесты `SerpStep` проходят локально.
- Часть integration/smoke тестов в текущем окружении пропущена из-за недоступного тестового Postgres (`TEST_DATABASE_URL`).
- `frontend` typecheck ограничен runtime Node в окружении (ошибка `Unexpected token ?`).
