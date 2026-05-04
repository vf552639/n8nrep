# Апрель 2026 — DOCX одиночной статьи/задачи: шапка H1 и строка Title в таблице

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**`app/services/docx_builder.py` (`build_single_article_docx`, `_add_simple_article_meta_table`):**
- Первая строка документа (крупный заголовок по центру, Pt(22)): значение **H1** из **`_get_all_meta_from_task(task, article)`**; если пусто — прежний **`display_title`** (`article.title` / ключ / «Article»). Так отделяется **SEO Title** (в таблице) от **H1** страницы.
- Мета-таблица: **Keyword**, **Word Count**, **Title** (meta title из **`_get_all_meta_from_task`**, иначе fallback на **`display_title`**), **Description**. Параметр **`title`** у **`_add_simple_article_meta_table`**.
- При отсутствии **`task`** метаданные из шагов не подтягиваются: шапка и строка Title в таблице совпадают с **`display_title`**.

---
