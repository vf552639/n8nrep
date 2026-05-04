# 6 апреля 2026 — Pipeline Presets (набор шагов per страница блупринта)

**Дата:** 2026-04-06
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема (закрыта):** один глобальный режим «SERP / не SERP» для всех страниц без SERP не подходил для About, Legal, Category vs полной статьи.

**База данных и модель**
- Таблица **`blueprint_pages`**: **`pipeline_preset`** (`VARCHAR(20)`, default **`full`**) — одно из: **`full`**, **`category`**, **`about`**, **`legal`**, **`custom`**; **`pipeline_steps_custom`** (JSONB, массив строк `agent_name` или `NULL` для пресетов).
- Миграция **`l6m7n8o9p0qc_add_pipeline_preset_to_blueprint_pages`**: добавление колонок + перенос существующих строк по **`use_serp`** / **`page_type`** / **`page_slug`** (legal → about → category).

**Backend**
- **`app/services/pipeline_presets.py`** — словари пресетов, **`resolve_pipeline_steps`**, **`resolve_steps_from_payload`**, **`pipeline_steps_use_serp`** (по факту наличия шагов SERP/scraping).
- **`app/services/pipeline.py`** — у задачи с **`blueprint_page_id`** список шагов из страницы; **`PHASE_REGISTRY`** + цикл **`run_pipeline`**; в **`step_results`** пишется **`_pipeline_plan: { "steps": [...] }`** для прогресса и UI.
- Пресет **`full`**: полный SEO-путь **без** `interlinking_citations`, image-цепочки и **`content_fact_checking`** (их можно включить только в **`custom`**). **`category`**: SERP + scraping + `final_structure_analysis` + генерация + `final_editing` + `html_structure` + `meta_generation`. **`about`**: **`primary_generation_about`** + **`meta_generation`**. **`legal`**: **`primary_generation_legal`** + **`meta_generation`** (перед вызовом — **`inject_legal_template_vars`**).
- Новые агенты: **`primary_generation_about`**, **`primary_generation_legal`** — константы и **`CRITICAL_VARS`** в **`pipeline_constants.py`**; промпты в **`scripts/seed_prompts.py`** (при вставке — **`max_tokens_enabled`**, **`temperature_enabled`** где задано в seed).
- **`phase_final_editing`**: если нет **`improver`**, fallback на **`primary_generation`**; для **`use_serp=false`** — также **`primary_generation_about` / `primary_generation_legal`**.
- **`phase_html_structure`** / **`phase_meta_generation`** / сборка статьи: выбор HTML из цепочки шагов с учётом about/legal (см. **`pick_html_for_meta`**, **`pick_structured_html_for_assembly`**).
- **`phase_content_fact_checking`**: при **`FACT_CHECK_ENABLED=false`** сохраняется завершённый «skipped»-результат, чтобы **`run_phase`** не вызывал шаг повторно при кастомном списке.
- **`PipelineContext`**: страница блупринта загружается по **`blueprint_page_id`** даже без **`project_id`**; **`all_site_pages`** — по **`blueprint_id`** страницы.

**API**
- **`app/api/blueprints.py`** — в create/update страницы: **`pipeline_preset`**, **`pipeline_steps_custom`**; **`use_serp`** пересчитывается с сервера по резолву шагов.
- **`app/api/projects.py`** — preview страниц: поля **`pipeline_preset`**, **`use_serp`** от резолва.
- **`app/api/tasks.py`** — **`calculate_progress`**: при наличии **`_pipeline_plan.steps`** прогресс = доля завершённых шагов из плана; иначе прежняя эвристика.

**Frontend**
- **`frontend/src/lib/pipelineSteps.ts`** — канонический порядок шагов для custom UI и **`orderedStepKeysFromResults`**.
- **`BlueprintsPage`**: колонка **Pipeline**, выбор пресета и чекбоксы для **`custom`**.
- **`StepMonitor`**: список шагов из **`_pipeline_plan`** или из ключей **`step_results`** (упорядоченно).
- **`PromptsPage`**: агенты **`primary_generation_about`**, **`primary_generation_legal`** в карте и порядке.
- **`TaskDetailPage`**: **Article Review** и **Export DOCX** учитывают черновики about/legal.

**DOCX**
- **`content_from_step_results_fallback`** — добавлены ключи **`primary_generation_about`**, **`primary_generation_legal`**.

**Обратная совместимость:** одиночные задачи без блупринта — как раньше: **`full`** при **`use_serp=true`**, иначе цепочка **`primary_generation` → `final_editing` → `html_structure` → `meta_generation`**. Глобальный **`skip_in_pipeline`** на промпте по-прежнему отключает шаг.

---
