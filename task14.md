# ТЗ: Исправление UI для Image-шагов пайплайна

---

## Контекст и текущее состояние

В предыдущем ТЗ (task13) была ошибка в архитектуре отображения image-шагов. 
Сейчас в UI есть агент **"Image Prompt Generation"** на вкладке Prompts, но он **не нужен пользователю напрямую** — это внутренний LLM-шаг, который генерирует промпты для Midjourney. Пользователь не должен его видеть и редактировать наравне с основными агентами.

Вместо этого пользователю нужен **"Image Generation"** — единый агент на вкладке Prompts, который управляет всей image-цепочкой.

### Текущая ситуация (что есть сейчас)

```
PromptsPage (Available Agents):
  ✅ AI Structure Analysis
  ✅ Chunk Cluster Analysis
  ✅ Competitor Structure
  ✅ Final Structure Analysis
  ✅ Structure Fact-Checking
  ✅ Image Prompt Generation    ← ЕСТЬ, но НЕ НУЖЕН пользователю
  ❌ Image Generation            ← НЕТ, но НУЖЕН
  ✅ Primary Generation
  ... (остальные агенты)

StepMonitor (Pipeline tab в Task):
  ✅ Image Prompt Generation     ← показывается, но ничего не делает визуально
  ✅ Image Generation            ← показывается
  ✅ Image Inject                ← показывается

TaskDetailPage (Prompts Debug tab):
  ❌ image_prompt_generation     ← НЕ добавлен (пропущен в предыдущем ТЗ)
```

### Целевое состояние (что должно быть)

```
PromptsPage (Available Agents):
  ✅ AI Structure Analysis
  ✅ Chunk Cluster Analysis
  ✅ Competitor Structure
  ✅ Final Structure Analysis
  ✅ Structure Fact-Checking
  ✅ Image Generation            ← ЗАМЕНЯЕТ Image Prompt Generation
  ✅ Primary Generation
  ... (остальные агенты)

StepMonitor (Pipeline tab в Task):
  ❌ Image Prompt Generation     ← УБРАТЬ из отображения
  ✅ Image Generation            ← остаётся
  ✅ Image Inject                ← остаётся

TaskDetailPage (Prompts Debug tab):
  ✅ image_prompt_generation     ← добавить (для технической отладки)
```

---

## Задача 1: PromptsPage.tsx — переименовать агент

**Файл:** `frontend/src/pages/PromptsPage.tsx`

### 1.1. Изменить в `AGENT_MAP`

**Было:**
```typescript
image_prompt_generation: "Image Prompt Generation",
```

**Стало:**
```typescript
image_prompt_generation: "Image Generation",
```

> **ВАЖНО:** Ключ `image_prompt_generation` остаётся прежним! Это `agent_name` в БД, 
> он используется в `call_agent()`, `seed_prompts.py`, `pipeline_constants.py`. 
> Менять ключ НЕЛЬЗЯ. Меняется только **отображаемое имя** (label) в UI.

### 1.2. AGENT_ORDER — без изменений

Порядок остаётся тем же:
```typescript
const AGENT_ORDER = [
  ...
  "structure_fact_checking",
  "image_prompt_generation",    // ← ключ тот же, просто label теперь "Image Generation"
  "primary_generation",
  ...
];
```

### 1.3. Проверка

После изменения на странице `/prompts` в списке **Available Agents** между 
"Structure Fact-Checking" и "Primary Generation" должен отображаться **"Image Generation"** 
(вместо "Image Prompt Generation").

При клике на него — открывается тот же промпт из БД с `agent_name = "image_prompt_generation"`, 
с теми же полями (system_prompt, user_prompt, model, temperature и т.д.) — 
как у любого другого агента (Primary Generation и т.д.).

---

## Задача 2: StepMonitor.tsx — убрать Image Prompt Generation из Pipeline

**Файл:** `frontend/src/components/tasks/StepMonitor.tsx`

### 2.1. Убрать `image_prompt_generation` из `ALL_STEPS`

**Было:**
```typescript
const ALL_STEPS = [
  "serp_research",
  "competitor_scraping",
  "ai_structure_analysis",
  "chunk_cluster_analysis",
  "competitor_structure_analysis",
  "final_structure_analysis",
  "structure_fact_checking",
  "image_prompt_generation",     // ← УБРАТЬ
  "image_generation",
  "primary_generation",
  ...
];
```

**Стало:**
```typescript
const ALL_STEPS = [
  "serp_research",
  "competitor_scraping",
  "ai_structure_analysis",
  "chunk_cluster_analysis",
  "competitor_structure_analysis",
  "final_structure_analysis",
  "structure_fact_checking",
  "image_generation",            // ← теперь сразу после structure_fact_checking
  "primary_generation",
  "competitor_comparison",
  "reader_opinion",
  "interlinking_citations",
  "improver",
  "final_editing",
  "content_fact_checking",
  "html_structure",
  "image_inject",
  "meta_generation"
];
```

> **ВАЖНО:** Убираем ТОЛЬКО из фронтенд-отображения. 
> Бэкенд (`pipeline_constants.py`, `ALL_STEPS` на сервере) — НЕ ТРОГАЕМ. 
> `image_prompt_generation` продолжает выполняться в пайплайне как обычно, 
> просто пользователь не видит его как отдельную карточку в StepMonitor.

### 2.2. Остальное — без изменений

Индикатор `isImagePaused` остаётся как есть — он привязан к `_pipeline_pause`, а не к конкретному шагу.

---

## Задача 3: TaskDetailPage.tsx — добавить image_prompt_generation в Prompts Debug

**Файл:** `frontend/src/pages/TaskDetailPage.tsx`

Эта задача **была пропущена** в предыдущей реализации. В массиве шагов на вкладке 
**"Prompts Debug"** нет `image_prompt_generation` — нужно добавить.

### 3.1. Найти массив шагов внутри `{activeTab === "prompts" && ...}`

**Было (текущий код):**
```typescript
{ id: "structure_fact_checking", label: "Structure Fact-Checking" },
{ id: "primary_generation", label: "Primary Generation" },
```

**Стало:**
```typescript
{ id: "structure_fact_checking", label: "Structure Fact-Checking" },
{ id: "image_prompt_generation", label: "Image Generation" },    // ← ДОБАВИТЬ
{ id: "primary_generation", label: "Primary Generation" },
```

> **Пояснение:** Здесь label — "Image Generation" (как на Prompts page), 
> а id — "image_prompt_generation" (agent_name из БД). 
> Prompts Debug показывает resolved system/user prompt, 
> которые есть только у LLM-агентов. `image_generation` (GoAPI сервис) и 
> `image_inject` (Python сервис) сюда НЕ добавляем — у них нет промптов.

---

## Задача 4: Streamlit `frontend/app.py` — переименовать агент

**Файл:** `frontend/app.py`

В функции `render_prompts()` в `agents_map` изменить label:

**Было:**
```python
"image_prompt_generation": "Генерация промптов для картинок",
```

**Стало:**
```python
"image_prompt_generation": "Генерация картинок",
```

---

## Задача 5: Пересборка и деплой frontend-react

После внесения всех изменений:

```bash
# 1. Убедиться что изменения закоммичены
git add frontend/src/pages/PromptsPage.tsx
git add frontend/src/components/tasks/StepMonitor.tsx
git add frontend/src/pages/TaskDetailPage.tsx
git add frontend/app.py
git commit -m "fix: rename Image Prompt Generation → Image Generation in UI, hide from StepMonitor, add to Prompts Debug"

# 2. Пересобрать Docker-образ БЕЗ кеша (важно!)
docker-compose build --no-cache frontend-react

# 3. Перезапустить контейнер
docker-compose up -d frontend-react

# 4. Проверить что новый код внутри контейнера
docker-compose exec frontend-react sh -c "grep -r 'image_prompt_generation' /app/dist/ | head -5"

# 5. В браузере: Ctrl+Shift+R (hard reload без кеша)
```

---

## Сводка изменений

```
Файл                           Что делаем
─────────────────────────────   ──────────────────────────────────────────
PromptsPage.tsx                 AGENT_MAP: label "Image Prompt Generation" → "Image Generation"
                                (ключ image_prompt_generation остаётся)

StepMonitor.tsx                 ALL_STEPS: удалить "image_prompt_generation" из массива
                                (image_generation и image_inject остаются)

TaskDetailPage.tsx              Prompts Debug tab: добавить 
                                { id: "image_prompt_generation", label: "Image Generation" }
                                после structure_fact_checking

frontend/app.py                 agents_map: label → "Генерация картинок"
```

### Что НЕ трогаем

- **Бэкенд** (`pipeline_constants.py`, `pipeline.py`, `tasks.py`) — без изменений
- **БД** (agent_name в таблице prompts) — остаётся `image_prompt_generation`
- **seed_prompts.py** — без изменений
- **Логика пайплайна** — `phase_image_prompt_gen` продолжает работать как LLM-агент, 
  `phase_image_gen` отправляет промпты в GoAPI, `phase_image_inject` вставляет в HTML

---

## Чеклист проверки

1. ☐ Открыть `/prompts` → в списке "Available Agents" виден **"Image Generation"** между "Structure Fact-Checking" и "Primary Generation"
2. ☐ Кликнуть на "Image Generation" → открывается промпт с полями system_prompt, user_prompt, model, temperature (как у Primary Generation)
3. ☐ Открыть любую задачу → вкладка **Pipeline** → шаг "Image Prompt Generation" **НЕ отображается**, шаги "Image Generation" и "Image Inject" — отображаются
4. ☐ Открыть любую задачу → вкладка **Prompts Debug** → "Image Generation" виден между "Structure Fact-Checking" и "Primary Generation", при раскрытии показывает resolved prompts
5. ☐ Streamlit (`/frontend`) → страница промптов → агент называется "Генерация картинок"
