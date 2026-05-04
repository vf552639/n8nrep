# 20 апреля 2026 — task40: гарантированные meta-теги и блок автора в финальном HTML

**Дата:** 2026-04-20
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** для страниц проектов без активной обёртки сайта (или при шаблоне без плейсхолдеров `title/description`) часть non-main страниц уходила в экспорт без корректного `<head>` (`<title>`, `<meta name="description">`). Также в финальном документе отсутствовали данные автора, хотя они используются в LLM-контексте.

**Backend — `app/services/template_engine.py`**
- Добавлена **`ensure_head_meta(html, title, description)`**: для полноценной страницы обновляет/вставляет `<title>` и `<meta name="description">` в `<head>`; для HTML-фрагмента оборачивает в минимальный `<!doctype html><html><head>...`.
- Добавлена **`render_author_footer(author, *, hide_geo=False)`**: формирует HTML-секцию `<section class="author-info">` со строками **Автор / Страна / Код страны / Город / Язык / Биография** (только непустые поля, с HTML-экранированием). С **мая 2026** при **`hide_geo=True`** строки **Страна / Код страны / Город** не выводятся (флаг **`blueprint_pages.hide_author_geo`**, см. раздел **«Май 2026 — Blueprint: per-page `hide_author_geo`»** выше).

**Backend — `app/services/pipeline` (сборка `GeneratedArticle.full_page_html`)**
- После `generate_full_page(...)` всегда вызывается **`ensure_head_meta(...)`**: и при `None` (шаблон не применён), и при успешной обёртке (подстраховка шаблонов без плейсхолдеров мета).
- В финальный документ инжектится author-footer (**`assembly._apply_author_footer`**): если есть `ctx.task.author_id`, блок вставляется перед первым `</body>`, иначе добавляется в конец строки; **`hide_geo`** берётся из **`ctx.blueprint_page.hide_author_geo`** при наличии страницы блупринта.

**Backend — `app/services/site_builder.py`**
- Добавлен warning-лог при fallback на `article.html_content`, если `full_page_html` пустой: помогает оперативно ловить регрессы сборки full-page HTML.

**Authors: модель / API / UI**
- Модель **`app/models/author.py`**: поле **`country_full`** (полное название страны).
- Миграция Alembic: **`u8v9w0x1y2zc_add_country_full_to_authors.py`**.
- Схема **`app/schemas/author.py`**: **`country_full`** в `AuthorCreate`.
- API **`app/api/authors.py`**: `GET /api/authors` возвращает `country_full`; `POST/PUT` читают и сохраняют `country_full`.
- UI **`frontend/src/pages/AuthorsPage.tsx`** и типы **`frontend/src/types/author.ts`**: добавлено поле формы **«Страна (полное название...)»** с привязкой к `country_full`.

**Тесты**
- Новый unit-файл: **`tests/services/test_template_engine.py`** — кейсы для `ensure_head_meta` (обёртка/обновление/идемпотентность/экранирование) и `render_author_footer`.
- Обновлён API-тест авторов: **`tests/api/test_authors_api.py`** (payload с `country_full`).

---
