# 2 апреля 2026 (вторая итерация) — Инфраструктура, API, React UI

**Дата:** 2026-04-02
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Инфраструктура**
- **Streamlit удалён:** файл **`frontend/app.py`** удалён, зависимость **`streamlit`** убрана из **`requirements.txt`**.
- **Docker Compose:** сервис **`frontend-react`** переименован в **`frontend`** (сборка из **`./frontend`**, порт **3000**). Отдельного контейнера Streamlit больше нет.
- В compose остаётся **5 сервисов:** `web`, `worker`, `beat`, `redis`, `frontend`.

**Backend**
- **`GET /api/tasks`:** ответ **`{ "items": [...], "total": N }`** (пагинация). Query: **`skip`**, **`limit`**, **`status`**, **`search`** (подстрока по **`main_keyword`**), **`site_id`**. Устранён дубликат ключа **`page_type`** в JSON элемента.
- **`PATCH /api/articles/{id}`:** правка **`html_content`**, опционально **`title`** / **`description`**; пересчёт **`word_count`** через **`count_content_words`**; при правке HTML сбрасывается **`full_page_html`**. В **`GET /api/articles/{id}`** в ответ добавлено поле **`full_page_html`**.
- **`GET /api/dashboard/stats`:** дополнительно **`cost_by_day`** — сумма **`total_cost`** по календарным дням (UTC) за последние ~30 дней для задач со статусом **`completed`** (группировка по дате **`updated_at`**).

**Frontend (React)**
- **`SiteDetailPage` (`/sites/:id`):** полная форма сайта (**name, domain, country, language, is_active**, выбор **`template_id`**, **legal_info** JSON); блок **глобальных HTML-шаблонов** с Add / Edit (Monaco) / Delete через **`/api/templates`** (шаблоны общие для всех сайтов, не вложенные в `/sites/.../templates`).
- **`TasksPage`:** серверная пагинация (**50** строк на страницу), поиск с debounce на бэкенде, фильтр по сайту через **`site_id`**; низ таблицы — Previous / Next и счётчик записей.
- **`ArticleDetailPage`:** **Download HTML**, **Export DOCX** (blob через axios с API key), **Edit HTML** (Monaco) + **Save** через **`PATCH`** (раньше ссылка «Export Word» с **`?format=docx`** не работала на бэкенде — см. раздел **DOCX: одиночная статья** выше).
- **`DashboardPage`:** столбчатый график (Recharts) по **`cost_by_day`**, если есть данные.
- **`TaskDetailPage`:** запрос **`GET /tasks/{id}/images`** выполняется и при паузе **`image_review`**, даже если вкладка открывается до финального статуса шага (улучшение загрузки превью).
- **`ProjectDetailPage`:** для задачи со статусом **`failed`** — кнопка **Retry page** (вызов **`POST /tasks/{id}/retry`**).
- **Маршрут `/seo-setup` удалён** (файл **`SeoSetupPage.tsx`**); нижний пункт **SEO Setup** в сайдбаре убран; заголовок сайдбара: **«SEO Content»**.

---
