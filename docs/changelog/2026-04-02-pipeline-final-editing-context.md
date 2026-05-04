# 2 апреля 2026 — Pipeline: контекст шага `final_editing`

**Дата:** 2026-04-02
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**`app/services/pipeline.py`, `phase_final_editing`:**
- Из **`editing_context`**, передаваемого в агент **`final_editing`**, убраны строки про **целевой объём по конкурентам** (`Target word count (competitor average): {avg_words}`) и **текущую статистику входного HTML** (слова/символы), чтобы не подталкивать модель к сокращению текста «до среднего по конкурентам».
- Переменные **`avg_words`**, **`input_word_count`**, **`input_char_count`** по-прежнему вычисляются и используются в **`add_log`** и **`save_step_result`** (метрики шага не менялись).

**Актуализация (апрель 2026) — без дублирования HTML/outline в `[CONTEXT]`:**
- **`editing_context`** для **`final_editing`** — **`""`**: текст статьи задаётся только через **`{{result_improver}}`** в user prompt из БД, структура — **`{{result_final_structure_analysis}}`** (из **`task.outline`** и/или **`step_results`**, см. ниже). Раньше тот же HTML и outline дублировались в **`[CONTEXT]`** и конфликтовали с промптом.
- **`call_agent`**: суффикс **`[CONTEXT]`** к user message добавляется только если **`context`** непустой после **`strip()`**.
- **`setup_template_vars`**: для каждого завершённого шага в **`step_results`** выставляется **`result_<ключ_шага>`**, если переменная ещё не задана или пустая (не перезаписывает непустые значения из **`task.outline`**, в т.ч. **`result_final_structure_analysis`**).
- В **`phase_final_editing`** после выбора тела статьи: **`ctx.template_vars["result_improver"] = improved_html`** — для **`use_serp=false`** нет шага **`improver`**, иначе **`{{result_improver}}`** оставался бы пустым.
- **`scripts/seed_prompts.py`**: обновлены system/user для **`final_editing`**; уже существующие строки в БД меняются вручную на странице **Prompts**.

---
