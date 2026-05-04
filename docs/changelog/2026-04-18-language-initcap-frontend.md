# 18 апреля 2026 — Language: INITCAP и защита на фронте

**Дата:** 2026-04-18
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема (закрыта):** в дропдаунах **Language** дублировались значения с разным регистром (**`French`** / **`french`**); при выборе нижнего регистра фильтр авторов по **`===`** не находил записей с **`French`**.

**База данных**
- Миграция **`s6t7u8v9w0xe_normalize_language_authors_sites`** (`down_revision`: **`r4s5t6u7v8wd`**): **`UPDATE authors SET language = INITCAP(TRIM(language)) …`**, то же для **`sites`**. **`downgrade`** — пустой (данные нормализованы необратимо без бэкапа).

**Backend**
- **`app/utils/language_normalize.py`** — функция **`normalize_language`** (trim + регистр по словам, в духе INITCAP).
- **`app/api/authors.py`** — **`AuthorCreate`**: **`field_validator("language")`** перед записью.
- **`app/api/sites.py`** — **`SiteCreate`** / **`SiteUpdate`**: валидаторы **`language`**.

**Frontend**
- **`frontend/src/lib/languageDisplay.ts`** — **`normalizeLanguageDisplay`**, **`languageEquals`**.
- **`ProjectsPage.tsx`**: список языков из нормализованных строк; **`filteredAuthors`** — страна в **UPPER**, язык через **`languageEquals`**.
- **`TasksPage.tsx`** (модалка создания задачи): то же для языков и авторов.
- **`SitesPage.tsx`** (модалка добавления сайта): нормализация списка языков из авторов.

**Тесты**
- **`tests/test_language_normalize.py`** — кейсы для **`normalize_language`**.

---
