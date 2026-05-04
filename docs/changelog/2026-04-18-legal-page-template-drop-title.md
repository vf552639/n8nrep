# 18 апреля 2026 — LegalPageTemplate: удаление поля `title`

**Дата:** 2026-04-18
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Цель:** единственный человекочитаемый идентификатор шаблона в списках и формах — **`name`** (плюс **`page_type`**); колонка **`title`** в БД и API убрана.

**База данных**
- Миграция **`q3r4s5t6u7vc_remove_title_from_legal_page_templates`** (`down_revision`: **`p2q3r4s5t6ub`**): **`DROP COLUMN title`** на **`legal_page_templates`**.

**Backend**
- **`app/models/template.py`**: у **`LegalPageTemplate`** нет **`title`**.
- **`app/api/legal_pages.py`**: схемы **`LegalPageCreate`** / **`LegalPageUpdate`** без **`title`**; ответы **`GET /`**, **`GET /by-page-type/...`**, **`GET /{id}`** и элементы **`for-blueprint` → `templates`** без **`title`**; **`POST /`** не записывает **`title`**.

**Frontend**
- **`frontend/src/types/template.ts`**, **`frontend/src/api/legalPages.ts`**, **`LegalPagesPage.tsx`**: форма, таблица и API без **`title`**.
- **`BlueprintsPage.tsx`**: в дропдауне legal-шаблонов отображается только **`name`**.

---
