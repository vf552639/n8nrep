# 18 апреля 2026 — Legal templates: дефолт на Blueprint, override в Project, фолбек в pipeline

**Дата:** 2026-04-18
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Цель:** три уровня выбора reference-шаблона для legal-страниц: явный выбор в проекте → дефолт страницы блупринта → генерация без reference.

**База данных и модель**
- Таблица **`blueprint_pages`**: колонка **`default_legal_template_id`** (UUID, FK → **`legal_page_templates.id`**, **`ON DELETE SET NULL`**, nullable).
- Миграция **`p2q3r4s5t6ub_add_default_legal_template_to_blueprint_pages`** (`down_revision`: **`n1o2p3q4r5sa`**).
- Модель **`app/models/blueprint.py`** — поле **`BlueprintPage.default_legal_template_id`**.

**Backend — `app/api/blueprints.py`**
- Схема **`BlueprintPageCreate`**: опциональный **`default_legal_template_id`** (строка UUID).
- **`_validate_default_legal_template`**: разрешено только при **`page_type ∈ LEGAL_PAGE_TYPES`**; шаблон должен существовать, **`is_active=True`**, **`page_type`** шаблона совпадает со страницей; при смене **`page_type`** на не-legal колонка обнуляется.
- **`GET /api/blueprints/{id}/pages`**: в каждой странице возвращается **`default_legal_template_id`** (строка или **`null`**).

**Backend — `app/api/legal_pages.py`**
- **`GET /api/legal-pages/for-blueprint/{blueprint_id}`**: для каждого элемента **`legal_page_types`** добавлено **`default_template_id`** — значение с первой страницы блупринта данного **`page_type`** (порядок **`sort_order`**, как и раньше для **`page_title`**).
- Элементы **`templates`** в ответе: **`{ id, name }`** (без отдельного **`title`** — см. блок **«LegalPageTemplate: удаление `title`»** ниже).

**Backend — `app/services/legal_reference.py`**
- **`inject_legal_template_vars`**: после чтения **`project.legal_template_map[page_type]`** (если пусто или нет ключа с непустым значением) — фолбек на **`BlueprintPage.default_legal_template_id`** по **`ctx.task.blueprint_page_id`**; загрузка **`LegalPageTemplate`** с проверкой **`page_type`** и **`is_active`**.

**Frontend**
- **`frontend/src/types/blueprint.ts`**, **`frontend/src/types/template.ts`**: новые поля; **`LEGAL_PAGE_TYPES_SET`** для условного UI.
- **`BlueprintsPage.tsx`**: селект **`page_type`** (article, category, homepage, legal-типы; опция «custom» для нестандартных значений из БД); при legal-типе — дропдаун **Default Legal Template** (`legalPagesApi.getByPageType`).
- **`ProjectsPage.tsx`**: при загрузке **`legal-for-blueprint`** — **`useEffect`** заполняет **`legal_template_map`** дефолтами из **`default_template_id`**, если пользователь ещё не выбрал ни одного шаблона; подсказка под селектом при наличии blueprint-дефолта.

---
