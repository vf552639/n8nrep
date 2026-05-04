# 2 апреля 2026 — Проекты: DOCX, additional keywords, формат meta_generation

**Дата:** 2026-04-02
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема (исправлено):** ответ `meta_generation` в виде `{"results": [{Title, Description, H1, Trigger}, …]}` не содержит ключей `title`/`description` на верхнем уровне — в **`pipeline.py`** при сборке статьи теперь из **первого элемента** `results` берутся Title/Description (и при отсутствии — предупреждения в лог); в **`GeneratedArticle.title` / `description`** попадают эти значения, в **`meta_data`** сохраняется **полный JSON** со всеми вариантами.

**Модель и миграция**
- **`site_projects.project_keywords`** (JSONB): пул доп. ключей, результат кластеризации по slug страниц, `unassigned`, при необходимости `clustering_model` / стоимость. Миграция **`j4k5l6m7n8oa_add_project_keywords_to_site_projects`**.

**Backend**
- **`app/config.py`:** `CLUSTERING_MODEL`, `MAX_PROJECT_KEYWORDS` (100).
- **`app/services/keyword_clusterer.py`** — один LLM-вызов, JSON-ответ с распределением ключей по страницам blueprint.
- **`POST /api/projects/cluster-keywords`** — preview кластеризации (без записи в БД).
- **`SiteProjectCreate`** / создание проекта: опционально **`project_keywords`**; клонирование копирует поле.
- **`process_project_page`** (`app/workers/tasks.py`) — слияние **`assigned_keywords`** в **`Task.additional_keywords`** с дедупликацией.
- **`app/services/docx_builder.py`** — один DOCX на проект: титул, оглавление, на каждую страницу таблица мета (Slug, Filename, Meta Title, Meta Description, **H1**, Keyword, Additional Keywords, Word Count; при **нескольких** вариантах в `results` — дополнительные строки Variant N Title/Description/H1/Trigger); контент из `html_content` или plain text / fallback `final_editing`.
- **`GET /api/projects/{id}/export-docx`** — требуется ≥1 задача со статусом `completed`; `Content-Disposition` с именем проекта.
- Зависимость **`python-docx`** (`requirements.txt`).

**Frontend**
- **`ProjectsPage`:** поле Additional Keywords, кнопка Cluster Keywords, превью распределения; при создании передаётся **`project_keywords`**.
- **`ProjectDetailPage`:** кнопка **Export DOCX** при `completed_tasks > 0` (рядом с CSV).

---
