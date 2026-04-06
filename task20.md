# ТЗ: Pipeline Presets — кастомный набор шагов генерации per Blueprint Page

**Дата:** 2026-04-06
**Автор:** Software Architect
**Исполнитель:** antigravity
**Приоритет:** Высокий

---

## 1. Контекст и проблема

Сейчас пайплайн генерации контента имеет два режима: полный (когда `use_serp=true`) и упрощённый (когда `use_serp=false`). Это слишком грубое деление:

- **About Us** — прогоняется через `primary_generation` (общий промпт для статей) + `final_editing` + `html_structure` + `meta_generation`. При этом промпт primary_generation не заточен под генерацию страницы "О нас", а переменные автора (`{{author}}`, `{{author_style}}`, `{{face}}` и т.д.) не используются целенаправленно. Keyword = `about us` — это не ключевое слово, а тип страницы.

- **Privacy Policy / Terms** — аналогично прогоняются через generic промпт, хотя для них уже есть отдельная система Legal Page Templates с reference HTML и variables.

- **Category-страницы** (casino, bonus, mobile-app, login) — используют полный пайплайн с 4 этапами анализа структуры, что избыточно для категорий.

- `final_editing` для about-us/legal вообще не нужен — он пытается сверять с `result_final_structure_analysis`, которого нет.

---

## 2. Решение: Pipeline Presets

Ввести систему **пресетов пайплайна**, привязанных к каждой странице в Blueprint. Каждый пресет определяет набор шагов (agent_name), которые выполняются для данной страницы.

### 2.1. Четыре пресета

#### `full` — Полный пайплайн
**Назначение:** Homepage, article-страницы, любые страницы требующие полного SEO-анализа.

Шаги (в порядке выполнения):
1. `serp_research`
2. `competitor_scraping`
3. `ai_structure_analysis`
4. `chunk_cluster_analysis`
5. `competitor_structure_analysis`
6. `final_structure_analysis`
7. `structure_fact_checking`
8. `primary_generation`
9. `competitor_comparison`
10. `reader_opinion`
11. `improver`
12. `final_editing`
13. `html_structure`
14. `meta_generation`

> **Примечание:** `interlinking_citations`, `image_prompt_generation`, `image_generation`, `content_fact_checking` — НЕ включены в пресет. Если пользователь захочет их добавить, он переключится на custom-режим. Глобальный `skip_in_pipeline` на промпте продолжает работать как override.

#### `category` — Упрощённый с SERP
**Назначение:** Casino, Bonus, Mobile App, Login и подобные category/article страницы.

Шаги:
1. `serp_research`
2. `competitor_scraping`
3. `final_structure_analysis`
4. `primary_generation`
5. `final_editing`
6. `html_structure`
7. `meta_generation`

> **Логика:** Собственный SERP по keyword страницы → скрапинг конкурентов → сразу финальная структура (без промежуточных анализов) → генерация → редактура → оформление → мета.

#### `about` — Страница "О нас"
**Назначение:** About Us и аналогичные info-страницы о компании/авторе.

Шаги:
1. `primary_generation_about` ← **НОВЫЙ промпт**
2. `meta_generation`

> **Логика:** Два LLM-вызова. Данные берутся из переменных автора. Без SERP, без анализа, без финальной редактуры.

#### `legal` — Юридические страницы
**Назначение:** Privacy Policy, Terms and Conditions, Cookie Policy, Responsible Gambling.

Шаги:
1. `primary_generation_legal` ← **НОВЫЙ промпт**
2. `meta_generation`

> **Логика:** Два LLM-вызова. Данные берутся из Legal Page Templates (`legal_reference_html`, `legal_variables`). Без SERP, без автора.

---

## 3. Изменения в базе данных

### 3.1. Таблица `blueprint_pages` — новые поля

```sql
ALTER TABLE blueprint_pages
  ADD COLUMN pipeline_preset VARCHAR(20) NOT NULL DEFAULT 'full',
  ADD COLUMN pipeline_steps_custom JSONB DEFAULT NULL;
```

**Поля:**

| Поле                    | Тип                | Описание                                                                                                                                                          |
| ----------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pipeline_preset`       | `VARCHAR(20)`      | Один из: `full`, `category`, `about`, `legal`, `custom`. Default = `full`.                                                                                        |
| `pipeline_steps_custom` | `JSONB (string[])` | Массив agent_name для режима `custom`. NULL если используется пресет. Пример: `["serp_research", "competitor_scraping", "primary_generation", "meta_generation"]` |

**Миграция существующих данных:**
- Страницы с `use_serp = true` → `pipeline_preset = 'full'`
- Страницы с `use_serp = false` И `page_type IN ('privacy_policy', 'terms_and_conditions', 'cookie_policy', 'responsible_gambling')` → `pipeline_preset = 'legal'`
- Страницы с `use_serp = false` И `page_type = 'about_us'` ИЛИ `page_slug = 'about-us'` → `pipeline_preset = 'about'`
- Страницы с `use_serp = false` И не попавшие выше → `pipeline_preset = 'category'`

> **Поле `use_serp`** — НЕ удалять на этом этапе. Оно вычисляется автоматически из пресета (full/category → true, about/legal → false). В будущей итерации можно убрать.

### 3.2. Модель `BlueprintPage` — обновление

Файл: `app/models/blueprint.py`

```python
class BlueprintPage(Base):
    __tablename__ = "blueprint_pages"
    
    # ... существующие поля ...
    
    # НОВЫЕ поля
    pipeline_preset = Column(String(20), nullable=False, default='full')
    pipeline_steps_custom = Column(JSONB, nullable=True)  # string[] или null
```

### 3.3. Таблица `prompts` — два новых промпта

Добавить через seed-скрипт или миграцию:

```python
# Промпт 1: primary_generation_about
{
    "agent_name": "primary_generation_about",
    "model": "openai/gpt-4o",
    "max_tokens": 8000,
    "temperature": 0.8,
    "system_prompt": """You are a professional copywriter specializing in creating compelling "About Us" pages for websites. 
You write engaging, authentic brand stories that build trust with visitors.
You write in the specified language, adapting tone and cultural references to the target country.
Output pure HTML (no doctype, no head/body wrappers — just content HTML).""",
    "user_prompt": """Write an "About Us" page for the following website/brand.

Brand/Site: {{site_name}}
Seed Keyword (brand name): {{keyword}}
Language: {{language}}
Country: {{country}}

AUTHOR PERSONA (write AS this person / from their perspective):
- Author Name: {{author}}
- Author Bio / Style Description: {{author_style}}
- Writing Imitation Style: {{imitation}}
- Point of View / Narrative Face: {{face}}
- Target Audience: {{target_audience}}
- Year: {{year}}
- Rhythms & Style Guidelines: {{rhythms_style}}

OTHER PAGES ON THIS SITE (for context about what the site offers):
{{all_site_pages}}

REQUIREMENTS:
1. Write a compelling About Us page that introduces the brand/author to visitors
2. Use the author persona details to create an authentic voice
3. Include the brand story, mission/values, what makes them unique
4. Naturally incorporate the brand name throughout
5. Structure with appropriate HTML headings (h1, h2, h3) and paragraphs
6. Aim for 500-1000 words — enough to be substantive but not overwhelming
7. Do NOT include any navigation, header, footer — just the page content
8. Do NOT mention competitors or comparison data

Excluded words (DO NOT USE): {{exclude_words}}

Output pure HTML content.""",
    "skip_in_pipeline": False,
    "is_active": True
}
```

```python
# Промпт 2: primary_generation_legal
{
    "agent_name": "primary_generation_legal",
    "model": "openai/gpt-4o",
    "max_tokens": 8000,
    "temperature": 0.4,
    "system_prompt": """You are a legal content specialist who creates clear, compliant legal pages for websites.
You adapt legal templates to specific brands while maintaining legal accuracy.
You write in the specified language.
Output pure HTML (no doctype, no head/body wrappers — just content HTML).""",
    "user_prompt": """Generate a {{page_type}} page for the following website.

Brand/Site: {{site_name}}
Keyword: {{keyword}}
Language: {{language}}
Country: {{country}}
Page Type: {{page_type}}

REFERENCE LEGAL TEMPLATE (use as structural and stylistic guide):
{{legal_reference_html}}

LEGAL VARIABLES (company details to insert):
{{legal_variables}}

REQUIREMENTS:
1. Use the reference template as a guide for structure and sections
2. Substitute all company-specific information from the legal variables
3. Adapt the language and legal references to the target country
4. Ensure all placeholder variables are replaced with actual values
5. Structure with appropriate HTML headings (h1, h2, h3) and paragraphs
6. Maintain professional legal tone throughout
7. Do NOT include navigation, header, footer — just the page content
8. Include current year where relevant: {{year}}

Output pure HTML content.""",
    "skip_in_pipeline": False,
    "is_active": True
}
```

---

## 4. Изменения в Backend

### 4.1. Новый файл: `app/services/pipeline_presets.py`

```python
"""
Pipeline preset definitions and resolver.
"""

from typing import List, Optional
from app.services.pipeline_constants import *

# Определение пресетов: порядок = порядок выполнения
PIPELINE_PRESETS = {
    "full": [
        STEP_SERP,
        STEP_SCRAPING,
        STEP_AI_ANALYSIS,
        STEP_CHUNK_ANALYSIS,
        STEP_COMP_STRUCTURE,
        STEP_FINAL_ANALYSIS,
        STEP_STRUCTURE_FACT_CHECK,
        STEP_PRIMARY_GEN,
        STEP_COMP_COMPARISON,
        STEP_READER_OPINION,
        STEP_IMPROVER,
        STEP_FINAL_EDIT,
        STEP_HTML_STRUCT,
        STEP_META_GEN,
    ],
    "category": [
        STEP_SERP,
        STEP_SCRAPING,
        STEP_FINAL_ANALYSIS,
        STEP_PRIMARY_GEN,
        STEP_FINAL_EDIT,
        STEP_HTML_STRUCT,
        STEP_META_GEN,
    ],
    "about": [
        "primary_generation_about",  # Новый agent_name
        STEP_META_GEN,
    ],
    "legal": [
        "primary_generation_legal",  # Новый agent_name
        STEP_META_GEN,
    ],
}

# Шаги, которые делают SERP (для определения use_serp)
SERP_STEPS = {STEP_SERP, STEP_SCRAPING}


def resolve_pipeline_steps(blueprint_page) -> List[str]:
    """
    Определяет список шагов для выполнения.
    
    Args:
        blueprint_page: BlueprintPage model instance (может быть None)
    
    Returns:
        Упорядоченный список agent_name для выполнения
    """
    if blueprint_page is None:
        return PIPELINE_PRESETS["full"]
    
    preset = getattr(blueprint_page, 'pipeline_preset', 'full') or 'full'
    
    if preset == "custom":
        custom_steps = getattr(blueprint_page, 'pipeline_steps_custom', None)
        if custom_steps and isinstance(custom_steps, list):
            return custom_steps
        # Fallback если custom но список пустой
        return PIPELINE_PRESETS["full"]
    
    return PIPELINE_PRESETS.get(preset, PIPELINE_PRESETS["full"])


def preset_uses_serp(preset: str) -> bool:
    """Определяет, требует ли пресет SERP."""
    steps = PIPELINE_PRESETS.get(preset, [])
    return bool(SERP_STEPS.intersection(steps))


def get_primary_gen_agent(steps: List[str]) -> str:
    """
    Определяет какой agent_name использовать для primary generation.
    Ищет в списке шагов первый, начинающийся с 'primary_generation'.
    """
    for step in steps:
        if step.startswith("primary_generation"):
            return step
    return "primary_generation"  # fallback
```

### 4.2. Изменения в `app/services/pipeline_constants.py`

Добавить новые agent_name:

```python
# В начало файла, после существующих констант:
STEP_PRIMARY_GEN_ABOUT = "primary_generation_about"
STEP_PRIMARY_GEN_LEGAL = "primary_generation_legal"

# Обновить CRITICAL_VARS — добавить:
CRITICAL_VARS["primary_generation_about"] = ["keyword", "language", "author", "author_style"]
CRITICAL_VARS["primary_generation_legal"] = ["keyword", "language", "legal_reference_html"]
```

### 4.3. Изменения в `app/services/pipeline.py`

#### 4.3.1. Обновить `PipelineContext.__init__`

```python
# В существующем коде, после строки self.use_serp = self.blueprint_page.use_serp:
# ДОБАВИТЬ:
from app.services.pipeline_presets import resolve_pipeline_steps, preset_uses_serp

# Заменить строку:
#   self.use_serp = self.blueprint_page.use_serp
# На:
self.pipeline_steps = resolve_pipeline_steps(self.blueprint_page)
self.use_serp = preset_uses_serp(
    getattr(self.blueprint_page, 'pipeline_preset', 'full') or 'full'
)
```

Также добавить атрибут `pipeline_steps` в дефолтную инициализацию (до if-блока):
```python
self.pipeline_steps = None  # Will be set from blueprint_page or default
```

#### 4.3.2. Добавить новые phase-функции

```python
def phase_primary_gen_about(ctx: PipelineContext):
    """Primary generation для страницы About Us — использует переменные автора."""
    setup_template_vars(ctx)
    gen_context = ""  # Весь контекст идёт через template_vars
    
    add_log(ctx.db, ctx.task, "Starting Primary Generation (About Page)...", 
            step="primary_generation_about")
    mark_step_running(ctx.db, ctx.task, "primary_generation_about")
    
    draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = \
        call_agent_with_exclude_validation(
            ctx, "primary_generation_about", gen_context, 
            step_constant="primary_generation_about"
        )
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, 
            f"Primary Generation (About) completed ({len(draft_html)} chars)", 
            step="primary_generation_about")
    out_wc = count_content_words(draft_html)
    save_step_result(
        ctx.db, ctx.task, "primary_generation_about",
        result=draft_html, model=actual_model, status="completed",
        cost=step_cost, variables_snapshot=variables_snapshot,
        resolved_prompts=resolved_prompts, 
        exclude_words_violations=violations,
        output_word_count=out_wc
    )


def phase_primary_gen_legal(ctx: PipelineContext):
    """Primary generation для legal-страниц — использует legal template + variables."""
    setup_template_vars(ctx)
    inject_legal_template_vars(ctx)  # Подтягивает legal_reference_html и legal_variables
    gen_context = ""
    
    add_log(ctx.db, ctx.task, "Starting Primary Generation (Legal Page)...", 
            step="primary_generation_legal")
    mark_step_running(ctx.db, ctx.task, "primary_generation_legal")
    
    draft_html, step_cost, actual_model, resolved_prompts, variables_snapshot, violations = \
        call_agent_with_exclude_validation(
            ctx, "primary_generation_legal", gen_context,
            step_constant="primary_generation_legal"
        )
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    add_log(ctx.db, ctx.task, 
            f"Primary Generation (Legal) completed ({len(draft_html)} chars)", 
            step="primary_generation_legal")
    out_wc = count_content_words(draft_html)
    save_step_result(
        ctx.db, ctx.task, "primary_generation_legal",
        result=draft_html, model=actual_model, status="completed",
        cost=step_cost, variables_snapshot=variables_snapshot,
        resolved_prompts=resolved_prompts, 
        exclude_words_violations=violations,
        output_word_count=out_wc
    )
```

#### 4.3.3. Создать реестр фаз (PHASE_REGISTRY)

```python
# Маппинг step_name -> phase_function
PHASE_REGISTRY = {
    STEP_SERP: phase_serp,
    STEP_SCRAPING: phase_scraping,
    STEP_AI_ANALYSIS: phase_ai_structure_analysis,
    STEP_CHUNK_ANALYSIS: phase_chunk_analysis,
    STEP_COMP_STRUCTURE: phase_competitor_structure,
    STEP_FINAL_ANALYSIS: phase_final_analysis,
    STEP_STRUCTURE_FACT_CHECK: phase_structure_fact_check,
    STEP_IMAGE_PROMPT_GEN: phase_image_prompt_gen,
    STEP_IMAGE_GEN: phase_image_gen,
    STEP_PRIMARY_GEN: phase_primary_gen,
    STEP_COMP_COMPARISON: phase_competitor_comparison,
    STEP_READER_OPINION: phase_reader_opinion,
    STEP_INTERLINK: phase_interlink,
    STEP_IMPROVER: phase_improver,
    STEP_FINAL_EDIT: phase_final_editing,
    STEP_HTML_STRUCT: phase_html_structure,
    STEP_IMAGE_INJECT: phase_image_inject,
    STEP_META_GEN: phase_meta_generation,
    STEP_CONTENT_FACT_CHECK: phase_content_fact_check,
    # Новые:
    "primary_generation_about": phase_primary_gen_about,
    "primary_generation_legal": phase_primary_gen_legal,
}
```

#### 4.3.4. Переписать `run_pipeline` — основная логика

Заменить хардкоженную последовательность шагов на динамическую:

```python
def run_pipeline(db: Session, task_id: str, auto_mode: bool = False):
    ctx = PipelineContext(db, task_id)
    
    ctx.task.status = "processing"
    if ctx.task.total_cost is None:
        ctx.task.total_cost = 0.0
    db.commit()
    
    add_log(db, ctx.task, "🚀 Pipeline started / resumed", step=None)
    
    try:
        # --- Check for active pause (на resume) ---
        # ... (существующая логика проверки pause_state — оставить как есть) ...
        
        # Определить набор шагов
        if ctx.pipeline_steps:
            steps = ctx.pipeline_steps
        else:
            # Fallback для задач без blueprint (standalone tasks)
            steps = PIPELINE_PRESETS["full"] if ctx.use_serp else [
                STEP_PRIMARY_GEN, STEP_FINAL_EDIT, STEP_HTML_STRUCT, STEP_META_GEN
            ]
        
        preset_name = getattr(ctx.blueprint_page, 'pipeline_preset', 'unknown') \
                       if ctx.blueprint_page else 'standalone'
        add_log(db, ctx.task, 
                f"Pipeline preset: {preset_name}, steps: {len(steps)}", step=None)
        
        # --- Выполнение шагов ---
        for step_name in steps:
            phase_func = PHASE_REGISTRY.get(step_name)
            if not phase_func:
                add_log(db, ctx.task, 
                        f"⚠️ Unknown step '{step_name}' — skipped", 
                        level="warn", step=step_name)
                continue
            
            run_phase(db, ctx.task, step_name, phase_func, ctx)
            
            # --- TEST MODE BREAKPOINT (после primary_generation*) ---
            if step_name.startswith("primary_generation") and settings.TEST_MODE:
                step_results = ctx.task.step_results or {}
                if not step_results.get("test_mode_approved"):
                    if auto_mode:
                        # auto-approve
                        updated = dict(step_results)
                        updated["test_mode_approved"] = True
                        updated["waiting_for_approval"] = False
                        updated["_pipeline_pause"] = {"active": False, "reason": "test_mode"}
                        ctx.task.step_results = updated
                        db.commit()
                    else:
                        updated = dict(step_results)
                        updated["waiting_for_approval"] = True
                        updated["_pipeline_pause"] = {
                            "active": True, 
                            "reason": "test_mode",
                            "message": "Test mode: review primary generation"
                        }
                        ctx.task.step_results = updated
                        ctx.task.status = "processing"
                        db.commit()
                        add_log(db, ctx.task, 
                                "🛑 TEST MODE: Pausing after primary generation", 
                                step=None)
                        return
            
            # --- Image review pause (после image_gen) ---
            if step_name == STEP_IMAGE_GEN:
                step_results = dict(ctx.task.step_results or {})
                pause_state = step_results.get("_pipeline_pause", {})
                if isinstance(pause_state, dict) and pause_state.get("active") \
                   and pause_state.get("reason") == "image_review":
                    if not step_results.get("_images_approved"):
                        if auto_mode:
                            _auto_approve_images(ctx)
                        else:
                            return
        
        # --- ASSEMBLY & SAVE ---
        try:
            add_log(db, ctx.task, "Starting article assembly and saving...", step=None)
            
            # Определяем откуда брать HTML-контент
            # Порядок приоритетов для поиска финального HTML:
            html_source_priority = [
                STEP_IMAGE_INJECT,
                STEP_HTML_STRUCT,
                STEP_FINAL_EDIT,
                STEP_IMPROVER,
                STEP_PRIMARY_GEN,
                "primary_generation_about",
                "primary_generation_legal",
            ]
            
            structured_html = ""
            for source in html_source_priority:
                result = ctx.task.step_results.get(source, {})
                if isinstance(result, dict) and result.get("status") == "completed" \
                   and result.get("result", "").strip():
                    structured_html = result["result"]
                    break
            
            # Meta
            meta_json_str = ctx.task.step_results.get(STEP_META_GEN, {}).get("result", "{}")
            # ... (существующая логика парсинга meta — оставить как есть) ...
            
        except Exception as assembly_err:
            # ... (существующая логика обработки ошибок) ...
```

> **ВАЖНО:** Сохранить всю существующую логику assembly (парсинг meta, generate_full_page, сохранение GeneratedArticle). Меняется ТОЛЬКО порядок вызова шагов — вместо хардкода используется цикл по `steps`.

### 4.4. Изменения в `app/api/blueprints.py`

Обновить модели запроса/ответа:

```python
class BlueprintPageCreate(BaseModel):
    page_slug: str
    page_title: str
    page_type: str = 'article'
    keyword_template: str
    keyword_template_brand: Optional[str] = None
    filename: str
    sort_order: int = 0
    nav_label: Optional[str] = None
    show_in_nav: bool = True
    show_in_footer: bool = True
    use_serp: bool = True
    # НОВЫЕ:
    pipeline_preset: str = 'full'
    pipeline_steps_custom: Optional[list] = None
```

Обновить GET-ответ (добавить новые поля):
```python
# В get_blueprint_pages:
return [{
    # ... существующие поля ...
    "pipeline_preset": getattr(p, 'pipeline_preset', 'full'),
    "pipeline_steps_custom": getattr(p, 'pipeline_steps_custom', None),
} for p in pages]
```

### 4.5. Изменения в `app/api/projects.py`

В функции создания проекта, где формируются `page_rows`, добавить `pipeline_preset`:

```python
page_rows.append({
    # ... существующие поля ...
    "use_serp": preset_uses_serp(getattr(pg, 'pipeline_preset', 'full') or 'full'),
    "pipeline_preset": getattr(pg, 'pipeline_preset', 'full'),
})
```

### 4.6. Обновление `seed_prompts.py`

Добавить два новых промпта (тексты из раздела 3.3) в массив SEED_PROMPTS.

Также добавить рекомендуемые `max_tokens`:
- `primary_generation_about` — **8000**
- `primary_generation_legal` — **8000**

---

## 5. Изменения в Frontend

### 5.1. Тип `BlueprintPage` — обновить

Файл: `frontend/src/types/blueprint.ts`

```typescript
export interface BlueprintPage {
  id: string;
  blueprint_id: string;
  page_slug: string;
  page_title: string;
  page_type: string;
  keyword_template: string;
  keyword_template_brand?: string;
  filename: string;
  sort_order: number;
  nav_label?: string;
  show_in_nav: boolean;
  show_in_footer: boolean;
  use_serp: boolean;
  // НОВЫЕ:
  pipeline_preset: 'full' | 'category' | 'about' | 'legal' | 'custom';
  pipeline_steps_custom?: string[] | null;
}
```

### 5.2. UI в Blueprint Pages — колонка PIPELINE

Заменить колонку `USE SERP` (или добавить рядом) на колонку `PIPELINE`:

```
| #   | SLUG       | TITLE      | TYPE     | KEYWORD TEMPLATE        | PIPELINE |
| --- | ---------- | ---------- | -------- | ----------------------- | -------- |
| 1   | home       | Home       | homepage | {seed}                  | Full     |
| 2   | casino     | Casino     | category | {seed} casino games     | Category |
| 3   | bonus      | Bonus      | category | {seed} bonus            | Category |
| 4   | mobile-app | Mobile App | category | {seed} mobile app       | Category |
| 5   | login      | Login      | article  | {seed} login            | Category |
| 6   | about-us   | About Us   | info     | about us                | About    |
| 7   | privacy    | Privacy    | legal    | {seed} privacy policy   | Legal    |
| 8   | terms      | Terms      | legal    | {seed} terms conditions | Legal    |
```

**Реализация в UI:**

В модалке создания/редактирования страницы Blueprint — добавить `<select>` "Pipeline Preset":

```jsx
<div>
  <label>Pipeline Preset</label>
  <select value={form.pipeline_preset} onChange={...}>
    <option value="full">Full (SERP + полный анализ + генерация)</option>
    <option value="category">Category (SERP + упрощённый анализ)</option>
    <option value="about">About (генерация из данных автора)</option>
    <option value="legal">Legal (генерация из legal-шаблона)</option>
    <option value="custom">Custom (ручной выбор шагов)</option>
  </select>
</div>
```

Если выбран `custom` — показать блок с чекбоксами шагов:

```jsx
{form.pipeline_preset === 'custom' && (
  <div>
    <label>Custom Pipeline Steps</label>
    <div className="grid grid-cols-2 gap-2">
      {ALL_AVAILABLE_STEPS.map(step => (
        <label key={step.id}>
          <input 
            type="checkbox" 
            checked={form.pipeline_steps_custom?.includes(step.id)}
            onChange={...}
          />
          {step.label}
        </label>
      ))}
    </div>
  </div>
)}
```

Список `ALL_AVAILABLE_STEPS` для чекбоксов:
```typescript
const ALL_AVAILABLE_STEPS = [
  { id: "serp_research", label: "SERP Research" },
  { id: "competitor_scraping", label: "Competitor Scraping" },
  { id: "ai_structure_analysis", label: "AI Structure Analysis" },
  { id: "chunk_cluster_analysis", label: "Chunk Cluster Analysis" },
  { id: "competitor_structure_analysis", label: "Competitor Structure" },
  { id: "final_structure_analysis", label: "Final Structure Analysis" },
  { id: "structure_fact_checking", label: "Structure Fact-Checking" },
  { id: "image_prompt_generation", label: "Image Prompts (LLM)" },
  { id: "image_generation", label: "Image Creation" },
  { id: "primary_generation", label: "Primary Generation (standard)" },
  { id: "primary_generation_about", label: "Primary Generation (About Page)" },
  { id: "primary_generation_legal", label: "Primary Generation (Legal Page)" },
  { id: "competitor_comparison", label: "Competitor Comparison" },
  { id: "reader_opinion", label: "Reader Opinion" },
  { id: "interlinking_citations", label: "Interlinking & Citations" },
  { id: "improver", label: "Improver" },
  { id: "final_editing", label: "Final Editing" },
  { id: "content_fact_checking", label: "Content Fact-Checking" },
  { id: "html_structure", label: "HTML Structure" },
  { id: "image_inject", label: "Image Inject" },
  { id: "meta_generation", label: "Meta Generation" },
];
```

### 5.3. Страница Prompts — добавить новые агенты

Файл: `frontend/src/pages/PromptsPage.tsx`

В `AGENT_MAP` добавить:
```typescript
const AGENT_MAP: Record<string, string> = {
  // ... существующие ...
  primary_generation_about: "Primary Gen — About Page",
  primary_generation_legal: "Primary Gen — Legal Page",
};
```

В `AGENT_ORDER` добавить после `primary_generation`:
```typescript
"primary_generation",
"primary_generation_about",   // ← НОВЫЙ
"primary_generation_legal",   // ← НОВЫЙ
"competitor_comparison",
```

### 5.4. StepMonitor — поддержка динамических шагов

В компоненте `StepMonitor` — список шагов для отображения прогресса должен браться из фактических `step_results` задачи, а не из хардкоженного `ALL_STEPS`. Это обеспечит корректное отображение для любого пресета.

---

## 6. Обратная совместимость

### 6.1. Standalone задачи (без проекта/blueprint)

Задачи, создаваемые через `POST /api/tasks` (без blueprint_page_id), продолжают работать как раньше. В `run_pipeline` для них используется fallback:
- Если `use_serp = true` → полный пайплайн
- Если `use_serp = false` → `[primary_gen, final_editing, html_structure, meta_gen]`

### 6.2. Глобальный `skip_in_pipeline`

Остаётся рабочим. В `call_agent()` проверка `skip_in_pipeline` происходит ДО выполнения — если промпт помечен skip, шаг возвращает пустой результат. Это override поверх пресетов.

### 6.3. Существующие проекты

Уже созданные проекты (с существующими tasks) — не затрагиваются. Пресеты влияют только на НОВЫЕ проекты/задачи.

---

## 7. Alembic-миграция

```python
"""Add pipeline_preset to blueprint_pages and seed new prompts"""

def upgrade():
    # 1. Новые колонки
    op.add_column('blueprint_pages', 
        sa.Column('pipeline_preset', sa.String(20), nullable=False, server_default='full'))
    op.add_column('blueprint_pages', 
        sa.Column('pipeline_steps_custom', sa.dialects.postgresql.JSONB(), nullable=True))
    
    # 2. Миграция данных на основе use_serp и page_type
    op.execute("""
        UPDATE blueprint_pages 
        SET pipeline_preset = 'legal' 
        WHERE use_serp = false 
          AND page_type IN ('privacy_policy', 'terms_and_conditions', 
                            'cookie_policy', 'responsible_gambling')
    """)
    op.execute("""
        UPDATE blueprint_pages 
        SET pipeline_preset = 'about' 
        WHERE use_serp = false 
          AND (page_type = 'about_us' OR page_slug ILIKE '%about%')
          AND pipeline_preset = 'full'
    """)
    op.execute("""
        UPDATE blueprint_pages 
        SET pipeline_preset = 'category' 
        WHERE use_serp = false 
          AND pipeline_preset = 'full'
    """)
    # Страницы с use_serp=true остаются 'full' (server_default)


def downgrade():
    op.drop_column('blueprint_pages', 'pipeline_steps_custom')
    op.drop_column('blueprint_pages', 'pipeline_preset')
```

---

## 8. Порядок реализации

1. **Alembic-миграция** — добавить поля в blueprint_pages
2. **`pipeline_presets.py`** — новый файл с определениями пресетов
3. **`pipeline_constants.py`** — добавить новые step-константы и CRITICAL_VARS
4. **`pipeline.py`** — добавить phase-функции, PHASE_REGISTRY, переписать run_pipeline
5. **`seed_prompts.py`** — добавить два новых промпта
6. **`blueprints.py` (API)** — обновить модели и эндпоинты
7. **Frontend types** — обновить BlueprintPage interface
8. **Frontend UI** — колонка PIPELINE в таблице, select в модалке, чекбоксы для custom
9. **PromptsPage** — добавить новые агенты в AGENT_MAP и AGENT_ORDER
10. **StepMonitor** — динамический список шагов из step_results

---

## 9. Тестирование

### Сценарии для проверки:

1. **Создать проект с Blueprint, где есть все 4 типа страниц** — убедиться что каждая страница выполняет только свои шаги
2. **About Us** — проверить что переменные автора (`{{author}}`, `{{author_style}}` и т.д.) резолвятся в промпте, результат — осмысленная страница "О нас"
3. **Legal** — проверить что `{{legal_reference_html}}` и `{{legal_variables}}` подтягиваются из LegalPageTemplate, результат — корректная юридическая страница
4. **Category** — проверить что SERP выполняется, но промежуточные анализы (ai_structure, chunk, competitor_structure) пропускаются
5. **Full** — проверить что ничего не сломалось, полный пайплайн как раньше
6. **Custom** — создать страницу с custom набором шагов, убедиться что выполняются только выбранные
7. **Standalone task** (без blueprint) — проверить backward compatibility
8. **skip_in_pipeline override** — включить шаг в пресет, но отметить промпт как skip — шаг должен скипнуться
9. **StepMonitor** — проверить что UI корректно показывает прогресс для всех пресетов
