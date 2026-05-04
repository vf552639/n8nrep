# 2 апреля 2026 — DOCX: одиночная статья и одиночная задача

**Дата:** 2026-04-02
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Backend (`app/services/docx_builder.py`)**
- **`build_single_article_docx(article, task=None)`** — один `.docx`: шапка **H1** (из мета, см. раздел **«DOCX одиночной статьи: шапка H1»** выше), таблица мета (**Keyword**, **Word Count**, **Title**, **Description**), тело из HTML через **`_html_to_docx_body`** или plain через **`_add_plain_text_content`**; общая логика контента с **`_get_content_from_task`** и при необходимости fallback по шагам (**`html_structure` → `final_editing` → `primary_generation`**).
- **`build_task_export_docx(db, task)`** — если есть **`GeneratedArticle`** по **`task_id`**, экспорт через **`build_single_article_docx`**; иначе синтетическая статья из **`content_from_step_results_fallback`** (тот же приоритет шагов).

**API**
- **`GET /api/articles/{article_id}/download?format=docx`** — Word; без **`format`** или **`format=html`** — прежнее поведие (HTML). Неподдерживаемый **`format`** → **400**. Нет контента для DOCX → **400**.
- **`GET /api/tasks/{task_id}/export-docx`** — DOCX по задаче; **404** если задачи нет, **400** если нет ни статьи, ни черновика в **`step_results`**.

**Frontend**
- **`ArticleDetailPage`:** кнопка **Export DOCX** (`articlesApi.downloadBlob(id, "docx")`, blob + API key).
- **`TaskDetailPage`:** **Export DOCX** в шапке (рядом с Force Complete/Fail), видима при **`status === "completed"`** или непустом **`step_results.final_editing.result`**; **`tasksApi.exportDocx(id)`** (как у проектов).

---
