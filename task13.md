# ТЗ: Добавление агента image_prompt_generation в UI

---

## Контекст

В рамках интеграции генерации изображений появляются 3 новых шага пайплайна:

| Шаг                       | Тип                | Есть промпт в БД?                | Где показывать                                    |
| ------------------------- | ------------------ | -------------------------------- | ------------------------------------------------- |
| `image_prompt_generation` | LLM-агент          | ДА — system_prompt + user_prompt | **PromptsPage** + StepMonitor + Prompts Debug tab |
| `image_generation`        | Сервисный (GoAPI)  | НЕТ                              | **Только StepMonitor**                            |
| `image_inject`            | Сервисный (Python) | НЕТ                              | **Только StepMonitor**                            |

Сейчас нужно правильно добавить их во все соответствующие списки в UI.

---

## Задача 1: `PromptsPage.tsx` — добавить агент `image_prompt_generation`

Файл: `frontend/src/pages/PromptsPage.tsx`

### 1.1. Добавить в `AGENT_MAP`

```typescript
const AGENT_MAP: Record<string, string> = {
  ai_structure_analysis: "AI Structure Analysis",
  chunk_cluster_analysis: "Chunk Cluster Analysis",
  competitor_structure_analysis: "Competitor Structure",
  final_structure_analysis: "Final Structure Analysis",
  structure_fact_checking: "Structure Fact-Checking",
  image_prompt_generation: "Image Prompt Generation",    // ← НОВЫЙ
  primary_generation: "Primary Generation",
  competitor_comparison: "Competitor Comparison",
  reader_opinion: "Reader Opinion",
  interlinking_citations: "Interlinking & Citations",
  improver: "Improver",
  final_editing: "Final Editing",
  content_fact_checking: "Content Fact-Checking",
  html_structure: "HTML Structure",
  meta_generation: "Meta Generation",
};
```

Позиция: **после `structure_fact_checking`, перед `primary_generation`** — соответствует порядку в пайплайне.

### 1.2. Добавить в `AGENT_ORDER`

```typescript
const AGENT_ORDER = [
  "ai_structure_analysis",
  "chunk_cluster_analysis",
  "competitor_structure_analysis",
  "final_structure_analysis",
  "structure_fact_checking",
  "image_prompt_generation",    // ← НОВЫЙ
  "primary_generation",
  "competitor_comparison",
  "reader_opinion",
  "interlinking_citations",
  "improver",
  "final_editing",
  "content_fact_checking",
  "html_structure",
  "meta_generation",
] as const;
```

### 1.3. Добавить переменные в `PROMPT_VARIABLES`

В группу **"Pipeline Results"** добавить:

```typescript
{ name: "result_image_prompt_generation", desc: "Промпты для генерации картинок (JSON)" },
{ name: "result_image_generation", desc: "Результат генерации картинок (JSON с URL)" },
```

> НЕ добавлять `image_generation` и `image_inject` в AGENT_MAP/AGENT_ORDER — у них нет промптов.

---

## Задача 2: `StepMonitor.tsx` — добавить все 3 шага в прогресс пайплайна

Файл: `frontend/src/components/tasks/StepMonitor.tsx`

### 2.1. Обновить массив `ALL_STEPS`

```typescript
const ALL_STEPS = [
  "serp_research",
  "competitor_scraping",
  "ai_structure_analysis",
  "chunk_cluster_analysis",
  "competitor_structure_analysis",
  "final_structure_analysis",
  "structure_fact_checking",
  "image_prompt_generation",     // ← НОВЫЙ (LLM)
  "image_generation",            // ← НОВЫЙ (сервисный)
  "primary_generation",
  "competitor_comparison",
  "reader_opinion",
  "interlinking_citations",
  "improver",
  "final_editing",
  "content_fact_checking",
  "html_structure",
  "image_inject",                // ← НОВЫЙ (сервисный)
  "meta_generation"
];
```

Все три шага показываются как StepCard — с одинаковым UI (статус, время, стоимость).
Для сервисных шагов `cost` будет 0, модель — пусто. Это нормально.

### 2.2. Добавить индикатор image-паузы

В компоненте, рядом с существующим `isWaiting`:

```typescript
const isImageReview = (results as any)._pipeline_pause?.active === true 
  && (results as any)._pipeline_pause?.reason === "image_review";

// В JSX рядом с существующим isWaiting:
{isImageReview && (
  <span className="text-amber-600 text-xs font-medium">
    ⏸ Paused — see Image Review tab
  </span>
)}
```

---

## Задача 3: `TaskDetailPage.tsx` — Prompts Debug tab

Файл: `frontend/src/pages/TaskDetailPage.tsx`

В массив шагов на вкладке **"Prompts Debug"** добавить `image_prompt_generation`:

```typescript
{[
  { id: "serp_research", label: "SERP Research" },
  { id: "competitor_scraping", label: "Competitor Scraping" },
  { id: "ai_structure_analysis", label: "AI Structure Analysis" },
  { id: "chunk_cluster_analysis", label: "Chunk Cluster Analysis" },
  { id: "competitor_structure_analysis", label: "Competitor Structure Analysis" },
  { id: "final_structure_analysis", label: "Final Structure Analysis" },
  { id: "structure_fact_checking", label: "Structure Fact-Checking" },
  { id: "image_prompt_generation", label: "Image Prompt Generation" },  // ← НОВЫЙ
  { id: "primary_generation", label: "Primary Generation" },
  { id: "competitor_comparison", label: "Competitor Comparison" },
  { id: "reader_opinion", label: "Reader Opinion" },
  { id: "interlinking_citations", label: "Interlinking & Citations" },
  { id: "improver", label: "Improver" },
  { id: "final_editing", label: "Final Editing" },
  { id: "content_fact_checking", label: "Content Fact-Checking" },
  { id: "html_structure", label: "HTML Structure" },
  { id: "meta_generation", label: "Meta Generation" }
].map(step => { ... })}
```

> НЕ добавлять `image_generation` и `image_inject` сюда — у них нет промптов,
> вкладка Prompts Debug показывает resolved system/user prompt для LLM-агентов.

---

## Задача 4: Streamlit `frontend/app.py` — добавить агент в список

В функции `render_prompts()` добавить в `agents_map`:

```python
agents_map = {
    "ai_structure_analysis": "AI анализ структуры",
    "chunk_cluster_analysis": "Анализ кластера (Чанки)",
    "competitor_structure_analysis": "Анализ конкурентов",
    "final_structure_analysis": "Финальный анализ структуры",
    "structure_fact_checking": "Фактический анализ структуры",
    "image_prompt_generation": "Генерация промптов для картинок",  # ← НОВЫЙ
    "primary_generation": "Первичная генерация",
    "competitor_comparison": "Сравнение с конкурентами",
    "reader_opinion": "Мнение читателя",
    "interlinking_citations": "Перелинковка и цитаты",
    "improver": "Улучшайзер",
    "final_editing": "Финальная редактура",
    "content_fact_checking": "Факт-чекинг контента",
    "html_structure": "Структура HTML",
    "meta_generation": "Генерация мета-тегов",
}
```

---

## Сводка: что куда добавляется

```
                              PromptsPage   StepMonitor   Prompts Debug   Streamlit
                              (AGENT_MAP)   (ALL_STEPS)   (TaskDetail)    (agents_map)
image_prompt_generation          ✅              ✅             ✅             ✅
image_generation                 ❌              ✅             ❌             ❌
image_inject                     ❌              ✅             ❌             ❌
```

---

## Порядок выполнения

1. `PromptsPage.tsx` — AGENT_MAP + AGENT_ORDER + PROMPT_VARIABLES
2. `StepMonitor.tsx` — ALL_STEPS + индикатор image-паузы
3. `TaskDetailPage.tsx` — Prompts Debug tab
4. `frontend/app.py` — Streamlit agents_map
5. Проверить: открыть PromptsPage — агент "Image Prompt Generation" видён между Structure Fact-Checking и Primary Generation
6. Проверить: открыть TaskDetailPage → Pipeline — 3 новых шага видны в StepMonitor
7. Проверить: открыть TaskDetailPage → Prompts Debug — только image_prompt_generation видён (не image_generation, не image_inject)
