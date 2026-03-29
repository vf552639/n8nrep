# ТЗ: Фикс Content Loss в HTML Structure + Оптимизация моделей и самопроверки

**Приоритет:** CRITICAL  
**Контекст:** Шаг 16 (html_structure) теряет 70% контента (1744 → 518 слов). Причина — отсутствие `max_tokens` в LLM-вызове + неподходящая модель. Параллельно нужно решить проблему бесконечных ретраев самопроверки.

---

## Проблема 1: max_tokens не передаётся в LLM

### Диагноз

В `app/services/llm.py` → функция `generate_text()` **не принимает и не передаёт** параметр `max_tokens`. При этом:
- Модель `Prompt` имеет поле `max_tokens`
- `PromptCreate` (в `app/api/prompts.py`) принимает `max_tokens: Optional[int] = 2000`
- Но в `call_agent()` (pipeline.py) это поле **никогда не читается** из объекта `prompt` и не передаётся в `generate_text()`

Результат: OpenRouter использует дефолт модели (часто 2048-4096 токенов), чего катастрофически мало для статьи в 1744 слова + HTML-шаблон.

### Что сделать

**Файл `app/services/llm.py`:**

1. Добавить параметр `max_tokens: Optional[int] = None` в сигнатуру `generate_text()`
2. Если `max_tokens` передан — добавлять `"max_tokens": max_tokens` в `kwargs` перед вызовом API
3. Если НЕ передан — **не добавлять** (пусть OpenRouter использует максимум модели)

```python
def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str = settings.DEFAULT_MODEL,
    temperature: float = 0.7,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    top_p: float = 1.0,
    max_retries: int = 3,
    max_tokens: Optional[int] = None,  # <-- ДОБАВИТЬ
    response_format: Optional[Dict[str, str]] = None
) -> Tuple[str, float, str, Optional[Dict[str, Any]]]:
```

В блоке формирования `kwargs`:
```python
if max_tokens is not None:
    kwargs["max_tokens"] = max_tokens
```

**Файл `app/services/pipeline.py` → функция `call_agent()`:**

1. Читать `prompt.max_tokens` из объекта Prompt
2. Передавать в `generate_text()`:

```python
kwargs = {
    "system_prompt": system_text,
    "user_prompt": user_msg,
    "model": prompt.model,
    "temperature": prompt.temperature,
    "frequency_penalty": prompt.frequency_penalty,
    "presence_penalty": prompt.presence_penalty,
    "top_p": prompt.top_p,
}
# ДОБАВИТЬ:
if prompt.max_tokens and prompt.max_tokens > 0:
    kwargs["max_tokens"] = prompt.max_tokens

if response_format:
    kwargs["response_format"] = response_format

res, cost, model, _ = generate_text(**kwargs)
```

**Файл `app/api/prompts.py` → эндпоинт `POST /test`:**

Аналогично передавать `max_tokens` в `generate_text()` при тестировании промптов (сейчас не передаётся).

### Рекомендуемые значения max_tokens для агентов

Обновить seed-промпты или через UI для каждого агента:

| Agent                         | Рекомендуемый max_tokens |
| ----------------------------- | ------------------------ |
| html_structure                | 16000                    |
| primary_generation            | 16000                    |
| improver                      | 16000                    |
| final_editing                 | 16000                    |
| competitor_comparison         | 4000                     |
| reader_opinion                | 4000                     |
| ai_structure_analysis         | 8000                     |
| chunk_cluster_analysis        | 4000                     |
| competitor_structure_analysis | 4000                     |
| final_structure_analysis      | 8000                     |
| structure_fact_checking       | 4000                     |
| content_fact_checking         | 4000                     |
| meta_generation               | 1000                     |
| interlinking_citations        | 4000                     |
| image_prompt_generation       | 2000                     |

---

## Проблема 2: Выбор модели для html_structure

### Суть

`html_structure` — это шаг "вставить контент в HTML-шаблон". Задача чисто техническая: взять готовую статью и шаблон сайта, объединить. Модель должна:
- Иметь **большое контекстное окно** (статья + шаблон = 5-15k токенов на вход)
- Иметь **большой output limit** (статья + шаблон обратно = 10-20k токенов на выход)  
- Быть **дешёвой** (задача не творческая)
- Точно следовать инструкциям, не обрезая и не переписывая контент

### Рекомендация

**Основная модель:** `google/gemini-2.5-flash` через OpenRouter

Причины:
- 1M контекст, до 65k output tokens
- Цена ~$0.075/1M input, ~$0.30/1M output (в 10x дешевле GPT-4o)
- Отлично справляется с техническими задачами "вставь A в B"
- Уже используется как `ANALYST_MODEL` в проекте

**Fallback:** `google/gemini-2.5-pro` — дороже, но надёжнее для сложных шаблонов.

### Что сделать

1. В UI (Prompts → html_structure) сменить модель с `openai/gpt-4o` на `google/gemini-2.5-flash`
2. Установить `max_tokens: 16000` для этого агента
3. Или обновить через seed:

```python
{
    "agent_name": "html_structure",
    "model": "google/gemini-2.5-flash",  # <-- БЫЛО openai/gpt-4o
    "max_tokens": 16000,                  # <-- ДОБАВИТЬ
    "temperature": 0.3,                   # <-- СНИЗИТЬ (задача техническая)
    ...
}
```

### Стоит ли подключать Google AI Studio API напрямую?

**Да, но не срочно.** Вот анализ:

| Параметр              | OpenRouter                     | Google AI Studio прямой                            |
| --------------------- | ------------------------------ | -------------------------------------------------- |
| Цена Gemini 2.5 Flash | ~$0.075/1M in, $0.30/1M out    | $0.015/1M in, $0.0625/1M out (в 5x дешевле!)       |
| Цена Gemini 2.5 Pro   | ~$1.25/1M in, $5/1M out        | $1.25/1M in, $10/1M out (паритет/дороже на output) |
| Лимиты rate           | Зависит от тарифа OpenRouter   | 1500 RPM (free), pay-as-you-go без лимита          |
| Удобство              | Единый клиент для всех моделей | Отдельный клиент, другой API-формат                |

**Рекомендация по приоритету:**
1. **Сейчас:** Просто переключить модель в OpenRouter на `google/gemini-2.5-flash` — это займёт 2 минуты
2. **Следующий спринт:** Добавить поддержку прямого Google AI API как второй провайдер для экономии на Flash-моделях

### Если решите добавить прямой Google API (отдельная задача на потом)

**Файл `app/services/llm.py`:**

1. Добавить новый параметр в `Settings`: `GOOGLE_AI_API_KEY: str = ""`
2. Создать второй клиент `get_google_client()` через `google.generativeai` или через OpenAI-совместимый эндпоинт Google: `https://generativelanguage.googleapis.com/v1beta/openai/`
3. В `generate_text()` определять провайдера по префиксу модели:
   - `google/...` → проверить `GOOGLE_AI_API_KEY`, если есть — прямой Google, иначе OpenRouter
   - Остальные → OpenRouter

```python
def _get_client_for_model(model: str) -> Tuple[OpenAI, str]:
    """Возвращает (client, clean_model_name) на основе провайдера."""
    if model.startswith("google/") and settings.GOOGLE_AI_API_KEY:
        # Прямой Google AI Studio через OpenAI-совместимый endpoint
        client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=settings.GOOGLE_AI_API_KEY,
        )
        # Google API не использует префикс "google/"
        clean_model = model.replace("google/", "")
        return client, clean_model
    else:
        return get_openai_client(), model
```

**Файл `app/config.py`:**
```python
GOOGLE_AI_API_KEY: str = ""
```

**Файл `app/api/settings_api.py`:**
Добавить `GOOGLE_AI_API_KEY` в `SettingsUpdate`.

**Файл `frontend/src/pages/SettingsPage.tsx`:**
Добавить поле ввода для Google AI API Key в секцию Integrations.

---

## Проблема 3: Самопроверка съедает бюджет

### Суть

Текущая `call_agent_with_exclude_validation()` делает ретрай всего агента целиком, если найдены exclude words. Это умеренно — всего `max_retries=1`.

Но проблема content loss (70%) сейчас **только логируется как warning**, а не триггерит ретрай. Если добавить ретрай на content loss по аналогии с exclude words — система будет:
1. Генерить полный HTML (стоит $0.02-0.05)
2. Видеть loss 60%
3. Ретраить → loss 55%
4. Ретраить → loss 50%
5. ... и так 20-30 раз, пока не дойдёт до <7%, потратив $1-2 на один шаг

### Решение: Трёхуровневая стратегия восстановления контента

**НЕ делать наивный retry цикл.** Вместо этого:

#### Уровень 1: Предотвращение (бесплатно)

Улучшить промпт `html_structure`, чтобы модель не обрезала контент. Добавить в system_prompt:

```
CRITICAL RULE: You MUST preserve ALL content from the input article word-for-word. 
Do NOT summarize, shorten, or omit any paragraphs, lists, or sections.
Your job is ONLY to wrap the existing content in the HTML template structure.
The output MUST contain every sentence from the input article.
```

Установить `temperature: 0.1-0.3` (минимальная креативность для технической задачи).

#### Уровень 2: Детекция + однократный умный ретрай (дешёвый)

**Файл `app/services/pipeline.py` → функция `phase_html_structure()`:**

После получения `structured_html`, если `loss_pct > 7`:

```python
if input_wc > 0 and loss_pct > 7:
    add_log(ctx.db, ctx.task,
        f"Content loss {loss_pct:.1f}% detected, attempting recovery...",
        level="warn", step=STEP_HTML_STRUCT)
    
    # Один ретрай с усиленным промптом
    recovery_context = (
        f"PREVIOUS ATTEMPT FAILED: You lost {loss_pct:.1f}% of content words.\n"
        f"Input had {input_wc} words but your output only had {output_wc} words.\n\n"
        f"YOU MUST OUTPUT ALL {input_wc} WORDS from the article below.\n"
        f"Do NOT summarize or shorten. Insert the COMPLETE article into the template.\n\n"
        f"{html_struct_context}"
    )
    
    retry_html, retry_cost, retry_model, retry_prompts, retry_vars = call_agent(
        ctx, "html_structure", recovery_context, variables=ctx.template_vars
    )
    ctx.task.total_cost += retry_cost
    
    retry_wc = count_content_words(retry_html)
    retry_loss = ((input_wc - retry_wc) / input_wc * 100.0) if input_wc > 0 else 0.0
    
    if retry_loss < loss_pct:  # Если стало лучше — используем
        structured_html = retry_html
        output_wc = retry_wc
        loss_pct = retry_loss
        step_cost += retry_cost
        actual_model = retry_model
        add_log(ctx.db, ctx.task,
            f"Recovery improved: {retry_loss:.1f}% loss (was {loss_pct:.1f}%)",
            step=STEP_HTML_STRUCT)
```

**Максимум 1 ретрай — жёсткое ограничение.**

#### Уровень 3: Программная вставка контента (fallback, без LLM)

Если после ретрая loss всё ещё > 20%, использовать программный fallback **без дополнительного LLM-вызова**:

```python
if loss_pct > 20:
    add_log(ctx.db, ctx.task,
        f"Content loss still {loss_pct:.1f}% after retry. Using programmatic insert.",
        level="warn", step=STEP_HTML_STRUCT)
    
    structured_html = programmatic_html_insert(
        template_html=ctx.template_vars.get("site_template_html", ""),
        content_html=final_html
    )
    output_wc = count_content_words(structured_html)
```

Создать новую функцию `programmatic_html_insert()`:

**Файл `app/services/html_inserter.py` (новый):**

```python
from bs4 import BeautifulSoup

def programmatic_html_insert(template_html: str, content_html: str) -> str:
    """
    Программно вставляет контент в шаблон без LLM.
    Ищет {{content}} placeholder или стандартные контейнеры.
    """
    if not template_html:
        return content_html
    
    # Вариант 1: Плейсхолдер {{content}}
    if "{{content}}" in template_html:
        return template_html.replace("{{content}}", content_html)
    
    # Вариант 2: Ищем <main>, <article>, <div id="content">
    soup = BeautifulSoup(template_html, 'html.parser')
    
    containers = (
        soup.find('main') or
        soup.find('article') or
        soup.find('div', id='content') or
        soup.find('div', class_='content') or
        soup.find('div', class_='post-content') or
        soup.find('div', class_='entry-content')
    )
    
    if containers:
        containers.clear()
        containers.append(BeautifulSoup(content_html, 'html.parser'))
        return str(soup)
    
    # Вариант 3: Просто вернуть контент как есть
    return content_html
```

### Бюджет-лимит на самопроверку

Добавить в `app/config.py`:

```python
# Self-check budget limits
SELF_CHECK_MAX_RETRIES: int = 1          # Макс. ретраев на content loss
SELF_CHECK_MAX_COST_PER_STEP: float = 0.10  # Макс. $ на ретраи одного шага
```

В `call_agent_with_exclude_validation()` и в новом recovery-коде проверять:

```python
if total_retry_cost > settings.SELF_CHECK_MAX_COST_PER_STEP:
    add_log(ctx.db, ctx.task,
        f"Budget limit reached for retries (${total_retry_cost:.4f}). Using best result.",
        level="warn", step=step_constant)
    break
```

---

## Порядок выполнения

1. **Фикс max_tokens** (Проблема 1) — это корневая причина, фиксит 90% проблемы
2. **Смена модели** (Проблема 2) — переключить html_structure на gemini-2.5-flash + temp 0.3
3. **Трёхуровневая защита** (Проблема 3) — промпт → 1 ретрай → программный fallback
4. **Google AI Studio** — отложить на следующий спринт, сначала проверить эффект от пунктов 1-3

## Ожидаемый результат

- Content loss в html_structure: **< 3%** (вместо 70%)
- Стоимость шага: **$0.002-0.005** (вместо $0.0018 с обрезкой, т.е. паритет но с полным контентом)
- Максимальная стоимость ретраев: **$0.10** (жёсткий лимит)
- Никаких бесконечных циклов самопроверки
