# 21 апреля 2026 — Legal: `primary_generation_legal`, inject, критичные переменные

**Дата:** 2026-04-21
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** у **`LegalPageTemplate`** контент образца может быть **plain text** или **HTML** (**`content_format`**), есть **`notes`**. Промпт **`primary_generation_legal`** и подстановки в пайплайне синхронизированы с моделью данных и UI.

**Backend — `app/services/legal_reference.py`**
- Стартовые ключи: **`legal_reference`**, **`legal_reference_html`** (тот же текст; совместимость со старыми промптами в БД, где осталось **`{{legal_reference_html}}`**), **`legal_reference_format`** (**`text`** / **`html`**), **`legal_template_notes`**, **`legal_variables`**.
- Для **`LEGAL_PAGE_TYPES`**: **`page_type_label`** — человекочитаемый тип (словарь **`PAGE_TYPE_LABELS`**, иначе **`title()`** от slug); выставляется **до** раннего **`return`** при **`use_serp`**, чтобы тип страницы был в контексте и при SERP.
- После резолва шаблона: **`substitute_legal_html`** подставляет **`site.legal_info`** в **`content`**, в переменные пишутся формат, **`notes`**, merge **`variables`** + **`legal_info`** в JSON **`legal_variables`**.

**Pipeline — `app/services/pipeline_constants.py`**, **`call_agent` в `app/services/pipeline.py`**
- **`CRITICAL_VARS["primary_generation_legal"]`**: **`keyword`**, **`language`**, **`country`**, **`page_type_label`**, **`legal_reference`**, **`legal_reference_format`**, **`legal_variables`**.
- **`CRITICAL_VARS_ALLOW_EMPTY`**: пустая **`legal_reference`** (генерация без образца) не помечается как «missing critical».

**Seed — `scripts/seed_prompts.py`**
- Обновлён текст **`primary_generation_legal`** под **`{{legal_reference}}`**, **`{{legal_reference_format}}`**, **`{{legal_template_notes}}`**, **`{{page_type_label}}`**.
- Агент в **`PROMPTS_FORCE_UPDATE`** — при **`python scripts/seed_prompts.py`** активная запись в БД получает тело из seed.

**Frontend — `frontend/src/pages/LegalPagesPage.tsx`**, **`frontend/src/pages/PromptsPage.tsx`**
- Редактор контента legal-шаблона: **`<textarea>`** при **Plain text**, **Monaco** при **HTML**.
- Variable Explorer: новые описания переменных legal (в т. ч. алиас **`legal_reference_html`**).

**Тесты:** **`tests/test_legal_reference_inject.py`**.

---
