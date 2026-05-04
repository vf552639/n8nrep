# 15 апреля 2026 — DOCX: тело статьи из шагов без «перехвата» `final_editing`

**Дата:** 2026-04-15
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема (закрыта):** при пустом **`article.html_content`** (реран, сборка не записалась и т.п.) **`_get_content_from_task`** уходил во внутренний **`from_final()`** и брал **только** результат шага **`final_editing`**, не доходя до **`content_from_step_results_fallback`**, где первым идёт **`html_structure`**. В итоге экспорт статьи/задачи в Word мог отдавать markdown/черновик вместо HTML после **`html_structure`** / **`image_inject`**.

**Backend (`app/services/docx_builder.py`)**
- **`_get_content_from_task`:** если **`article.html_content`** непустой — по-прежнему он; иначе сразу **`content_from_step_results_fallback(task)`** (убрана ветка «только `final_editing`»).
- **`content_from_step_results_fallback`:** порядок ключей **`step_results`** приведён к тому же, что **`pick_structured_html_for_assembly`** в **`pipeline.py`**: **`image_inject`** → **`html_structure`** → **`final_editing`** → **`improver`** → **`interlinking_citations`** → **`reader_opinion`** → **`competitor_comparison`** → **`primary_generation`** / **`primary_generation_about`** / **`primary_generation_legal`**.
- **`_resolve_single_article_body`:** удалён дублирующий второй вызов **`content_from_step_results_fallback`** при наличии **`task`** (источник тела уже полностью закрывается в **`_get_content_from_task`**).

**Примечание:** визуально DOCX по-прежнему «проще» HTML-превью из‑за конвертации **`_html_to_docx_body`** (ограниченный набор тегов → абзацы/заголовки/таблицы и т.д.) — это не регрессия источника контента.

---
