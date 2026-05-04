# 19 апреля 2026 — HTML-экспорт страниц (MODX / Source)

**Дата:** 2026-04-19
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** экспорт в DOCX искажает разметку при переносе в MODX; контент-менеджерам нужен **чистый HTML** тела страницы (как в **`GeneratedArticle.html_content`**, без обёртки сайта), с сохранением комментариев **`<!-- MEDIA: ... -->`** для ручной вставки изображений.

**Backend — `app/services/html_export.py`**
- **`resolve_export_body(task, article, for_html_export=...)`** — приоритет тела: **`article.html_content`** → извлечение из **`full_page_html`** (первый из **`main`** / **`article`** / **`body`**) → шаги в порядке **`image_inject`** → **`html_structure`** → **`final_editing`** → … (как **`pick_structured_html_for_assembly`** / бывший fallback в DOCX). При **`for_html_export=True`**: не-HTML в **`final_editing`** → **`HtmlExportNotReadyError`** (в API **409** «Page not ready for HTML export»).
- **`clean_html_for_paste`** — лёгкая чистка через BeautifulSoup (**`html.parser`**), без ломки HTML-комментариев; сериализация **`soup.decode(formatter="html5")`**.
- **`GET /api/tasks/{task_id}/export-html`** — только при **`task.status == "completed"`**, иначе **409**; **`Content-Type`**: **`text/html; charset=utf-8`**; **`Content-Disposition`**: **`{slug}.html`** (slug из **`blueprint_pages.page_slug`** или keyword); ответ с заголовком **`X-Export-Source`** (ключ источника тела).
- **`GET /api/projects/{project_id}/export-html`** — query **`mode`**: **`zip`** (по умолчанию) — архив **`{project_name}.html.zip`** с **`index.html`** (оглавление-ссылки) и **`{slug}.html`** на каждую завершённую страницу; **`concat`** — один файл **`{project_name}.html`** со склейкой и разделителями **`<!-- ===== PAGE: {slug} ===== -->`**. Права/условия как у **`/export-docx`** (нет завершённых страниц → **400**).

**`app/services/docx_builder.py`** — **`_get_content_from_task`** и экспорт задачи без строки **`GeneratedArticle`** вызывают **`resolve_export_body(..., for_html_export=False)`** (тот же приоритет, без строгого **409** для markdown в **`final_editing`** — DOCX отдаёт plain).

**Frontend** — **`frontend/src/api/tasks.ts`**: **`exportHtml`**, **`exportHtmlUrl`**, **`exportHtmlDownload`**; **`frontend/src/api/projects.ts`**: **`exportHtmlZip`**, **`exportHtmlConcat`**, URL-хелперы; **`TaskDetailPage`**: **Download HTML** / **Copy HTML** (при **`completed`**; **409** → тост; fallback-модалка с **textarea**, если clipboard недоступен); **`ProjectDetailPage`**: меню **Download HTML** — **All pages (ZIP)** / **Single file**.

**Тесты:** **`tests/test_html_export.py`** (пять кейсов для **`clean_html_for_paste`**).

---
