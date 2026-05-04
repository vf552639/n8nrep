# 23 апреля 2026 — Этап 1: task37 (API happy-path тесты)

**Дата:** 2026-04-23
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** вместо одного параметризованного smoke-теста по GET роутерам добавлен набор по-роутерных happy-path тестов для API с CRUD-сценариями и базовыми регрессиями по `tasks/projects`.

**Тестовая инфраструктура**
- **`tests/api/conftest.py`**: autouse-моки внешних сервисов (`llm` / `serp` / `scraper`), eager-настройка Celery, очистка `structlog.contextvars`, отключение worker health-check в API-тестах, привязка `factory_boy` к `api_db_session`.
- **`tests/factories.py`**: расширены фабрики (`ProjectFactory`, `BlueprintFactory`, `BlueprintPageFactory`, `PromptFactory`, `TemplateFactory`, `LegalPageTemplateFactory`, `ArticleFactory`) для покрытия CRUD и сценариев по роутерам.
- Для локального прогона API-тестов требуется dev-набор зависимостей (`factory-boy`, `pytest-asyncio`): `pip install -r requirements.txt -r requirements-dev.txt`.

**API test suite**
- Удалён legacy-файл **`tests/api/test_routers_happy_path.py`**.
- Добавлены роутерные файлы:  
  **`tests/api/test_health_api.py`**, **`test_dashboard_api.py`**, **`test_logs_api.py`**, **`test_sites_api.py`**, **`test_authors_api.py`**, **`test_templates_api.py`**, **`test_prompts_api.py`**, **`test_legal_pages_api.py`**, **`test_blueprints_api.py`**, **`test_articles_api.py`**, **`test_settings_api.py`**, **`test_tasks_api.py`**, **`test_projects_api.py`**.
- Корневой тест приложения перенесён в **`tests/test_app_routes.py`**.
- Добавлены сценарии регрессий: удаление задачи с повторным `404`, `delete-selected` для задач/проектов, archive/force-delete/reset-status для проектов.

**Документация**
- Обновлены **`docs/Roadmap.md`** и **`docs/PROJECT_OVERVIEW.md`** (замена упоминания `test_routers_happy_path` на пакет роутерных API-тестов из task37).

---
