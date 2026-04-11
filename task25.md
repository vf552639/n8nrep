# ТЗ: Исправление двух багов — meta_generation и Top P default

**Приоритет:** Высокий  
**Исполнитель:** antigravity  
**Дата:** 2026-04-11

---

## Баг 1: meta_generation не вернул Title и Description в статью

### Симптом

В логе пайплайна:
```
⚠️ meta_generation не вернул Title — используется keyword как fallback
⚠️ meta_generation не вернул Description
```

При этом сам шаг `meta_generation` отработал успешно: LLM вернул ответ (7278+7257 токенов, $0.08), шаг сохранён как `completed`. Значит данные есть, но парсер их не находит.

### Корневая причина

Проблема в функции `clean_and_parse_json()` в файле `app/services/json_parser.py`.

Эта функция содержит хардкод проверки на ключи `{"intent", "Taxonomy", "Attention", "structura"}` — ключи из шага `ai_structure_analysis`. Когда JSON не содержит этих ключей (а meta_generation возвращает `{"title", "description"}` или `{"results": [...]}`), функция выполняет "умный" поиск по вложенным словарям:

```python
required = {"intent", "Taxonomy", "Attention", "structura"}
if isinstance(data, dict):
    if not required.intersection(data.keys()):
        # Try to find them in the first nested dict
        for v in data.values():
            if isinstance(v, dict) and required.intersection(v.keys()):
                return v
    return data
```

На первый взгляд эта логика безвредна для meta_generation — она должна вернуть `data` as-is, поскольку ни одно вложенное значение не содержит `required` ключей.

**Однако реальная проблема в другом месте.** Модель `openai/gpt-5` (используется для meta_generation в данном прогоне) с `response_format={"type": "json_object"}` и reasoning-токенами (🧠 6528) может возвращать JSON в формате, отличном от ожидаемого промптом. 

Текущий промпт (из seed_prompts) ожидает:
```json
{"title": "...", "description": "..."}
```

Но пользователь мог кастомизировать промпт под формат с `results`:
```json
{"results": [{"Title": "...", "Description": "...", "H1": "...", "Trigger": "..."}]}
```

**Вероятные причины сбоя (проверить по порядку):**

1. **GPT-5 с reasoning возвращает обёртку.** Модели с reasoning-токенами могут оборачивать JSON в дополнительный объект (например `{"thinking": "...", "response": {"title": "..."}}`). Функция `clean_and_parse_json` не обрабатывает такие обёртки для meta_generation.

2. **Несовпадение регистра ключей.** Код в `pipeline.py` проверяет и `"Title"/"title"` и `"Description"/"description"`, но если GPT-5 вернёт `"TITLE"` или `"meta_title"` — ничего не найдётся.

3. **JSON невалиден, но частично.** `clean_and_parse_json` при `JSONDecodeError` возвращает `{}`. Если GPT-5 добавил trailing text после JSON — парсинг упадёт тихо.

### Что нужно сделать

#### 1. Добавить debug-лог сырого ответа meta_generation (КРИТИЧНО для диагностики)

**Файл:** `app/services/pipeline.py`, функция `phase_meta_generation`

Сразу после `call_agent` добавить лог первых 500 символов ответа (по аналогии с тем, как это сделано для `ai_structure_analysis`):

```python
def phase_meta_generation(ctx: PipelineContext):
    setup_template_vars(ctx)
    structured_html = pick_html_for_meta(ctx)
    meta_context = f"Article HTML:\n{structured_html}"
    add_log(ctx.db, ctx.task, "Generating Meta Tags (JSON)...", step=STEP_META_GEN)
    mark_step_running(ctx.db, ctx.task, STEP_META_GEN)
    meta_json_str, step_cost, actual_model, resolved_prompts, variables_snapshot = call_agent(
        ctx, "meta_generation", meta_context,
        response_format={"type": "json_object"}, variables=ctx.template_vars
    )
    ctx.task.total_cost = getattr(ctx.task, 'total_cost', 0.0) + step_cost
    
    # >>> ДОБАВИТЬ: debug лог сырого ответа
    add_log(
        ctx.db, ctx.task,
        f"meta_generation raw (first 500): {meta_json_str[:500]}",
        level="debug",
        step=STEP_META_GEN,
    )
    # <<< КОНЕЦ ДОБАВЛЕНИЯ
    
    add_log(ctx.db, ctx.task, f"Meta Tags Generation completed", step=STEP_META_GEN)
    save_step_result(...)
```

**Зачем:** Без этого лога невозможно понять, что именно вернула модель. Сейчас мы видим только финальный результат "Title не найден", но не видим сырой JSON.

#### 2. Сделать `clean_and_parse_json` универсальной — убрать хардкод `required` ключей

**Файл:** `app/services/json_parser.py`

Текущая версия:
```python
required = {"intent", "Taxonomy", "Attention", "structura"}
if isinstance(data, dict):
    if not required.intersection(data.keys()):
        for v in data.values():
            if isinstance(v, dict) and required.intersection(v.keys()):
                return v
    return data
```

**Заменить на:** Функция должна просто парсить JSON и возвращать результат. Логика поиска `required` ключей специфична для `ai_structure_analysis` и не должна быть в универсальном парсере.

```python
def clean_and_parse_json(text: str, unwrap_keys: set = None) -> Dict[str, Any]:
    """
    Parse JSON string, stripping markdown fences.
    If unwrap_keys provided, tries to find a nested dict containing those keys.
    """
    if not text:
        return {}
    
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    
    # Попытка найти JSON в тексте, если прямой парсинг не сработал
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Попробовать извлечь JSON из текста (модель могла добавить текст до/после)
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError as e:
                print(f"Warning: clean_and_parse_json failed: {e} | text[:200]={text[:200]}")
                return {}
        else:
            print(f"Warning: clean_and_parse_json no JSON found | text[:200]={text[:200]}")
            return {}
    
    if not isinstance(data, dict):
        return {}
    
    # Unwrap nested dict only if explicit keys requested
    if unwrap_keys:
        if not unwrap_keys.intersection(data.keys()):
            for v in data.values():
                if isinstance(v, dict) and unwrap_keys.intersection(v.keys()):
                    return v
    
    return data
```

**Далее** обновить вызов в `phase_ai_structure`:
```python
ai_struct_data = clean_and_parse_json(
    ai_structure, 
    unwrap_keys={"intent", "Taxonomy", "Attention", "structura"}
)
```

Все остальные вызовы `clean_and_parse_json` в пайплайне оставить без `unwrap_keys` — они будут работать как простой JSON-парсер.

#### 3. Улучшить извлечение title/description в assembly-блоке

**Файл:** `app/services/pipeline.py`, блок сборки статьи (assembly)

Добавить более устойчивый поиск title/description с fallback по вложенным структурам:

```python
meta_json_str = ctx.task.step_results.get(STEP_META_GEN, {}).get("result", "{}")
meta_data = clean_and_parse_json(meta_json_str)

# >>> ДОБАВИТЬ: debug лог распарсенных ключей
add_log(
    db, ctx.task,
    f"meta_data keys: {list(meta_data.keys()) if meta_data else 'EMPTY'}",
    level="debug",
    step=STEP_META_GEN,
)
# <<<

title = ""
description = ""

# Стратегия 1: {"results": [{Title, Description}, ...]}
if isinstance(meta_data.get("results"), list) and len(meta_data["results"]) > 0:
    first_variant = meta_data["results"][0]
    if isinstance(first_variant, dict):
        title = (
            first_variant.get("Title") or first_variant.get("title") or ""
        ).strip()
        description = (
            first_variant.get("Description") or first_variant.get("description") or ""
        ).strip()

# Стратегия 2: {"title": "...", "description": "..."}  (flat)
if not title:
    title = str(meta_data.get("title") or meta_data.get("Title") or "").strip()
if not description:
    description = str(
        meta_data.get("description") or meta_data.get("Description") or ""
    ).strip()

# >>> ДОБАВИТЬ Стратегия 3: поиск в любом вложенном dict (GPT-5 wrapping)
if not title and isinstance(meta_data, dict):
    for key, val in meta_data.items():
        if isinstance(val, dict):
            candidate_title = str(
                val.get("title") or val.get("Title") or ""
            ).strip()
            candidate_desc = str(
                val.get("description") or val.get("Description") or ""
            ).strip()
            if candidate_title:
                title = candidate_title
                description = description or candidate_desc
                add_log(
                    db, ctx.task,
                    f"meta title found in nested key '{key}'",
                    level="debug",
                    step=STEP_META_GEN,
                )
                break
# <<<

# ... далее существующие fallback'и с keyword
```

#### 4. Обновить тесты

**Файл:** `tests/test_pipeline.py` (или создать `tests/test_json_parser.py`)

Добавить тесты для новых сценариев:

```python
def test_json_parser_meta_flat():
    raw = '{"title": "Best Casino App", "description": "Download now"}'
    res = clean_and_parse_json(raw)
    assert res["title"] == "Best Casino App"

def test_json_parser_meta_results_array():
    raw = '{"results": [{"Title": "Best Casino", "Description": "Download"}]}'
    res = clean_and_parse_json(raw)
    assert res["results"][0]["Title"] == "Best Casino"

def test_json_parser_meta_wrapped():
    """GPT-5 may wrap JSON in a reasoning wrapper"""
    raw = '{"response": {"title": "Test", "description": "Desc"}, "confidence": 0.95}'
    res = clean_and_parse_json(raw)
    assert "response" in res  # парсер просто отдаёт dict, assembly разберётся

def test_json_parser_with_trailing_text():
    raw = '{"title": "Test"}\n\nHere is your JSON output.'
    res = clean_and_parse_json(raw)
    assert res.get("title") == "Test"

def test_json_parser_unwrap_keys():
    raw = '{"wrapper": {"intent": "transactional", "Taxonomy": "Casino"}}'
    res = clean_and_parse_json(raw, unwrap_keys={"intent", "Taxonomy", "Attention", "structura"})
    assert res["intent"] == "transactional"

def test_json_parser_no_unwrap_by_default():
    raw = '{"wrapper": {"intent": "transactional"}}'
    res = clean_and_parse_json(raw)
    assert "wrapper" in res  # без unwrap_keys — возвращает как есть
```

---

## Баг 2: Top P = 1 отображается когда параметр выключен

### Симптом

На скриншоте UI: Top P показывает значение `1` с выключенным тогглом. Это вводит в заблуждение — кажется, что Top P = 1.0 передаётся в API. Должно быть `0` (или пустое значение) когда тоггл выключен, чтобы визуально было понятно, что параметр не используется.

### Корневая причина

**Проблема в двух местах:**

#### 1. Backend: дефолтное значение `top_p` в модели Prompt

Поле `top_p` в модели `Prompt` имеет дефолт `1.0`. Когда `top_p_enabled=False`, значение всё равно хранится как `1.0` в БД и отдаётся на фронт.

В `prompt_llm_kwargs.py`:
```python
tpval = prompt.top_p if top_p is None else top_p
if tpval is None:
    tpval = 1.0  # <<< дефолт 1.0
eff_top_p = float(tpval)
```

Когда `top_p_enabled=False`, параметр НЕ передаётся в API (это правильно). Но значение `1.0` всё равно хранится и отдаётся на фронт.

#### 2. Frontend: при выключении тоггла сбрасывает на 1.0 вместо 0

В `PromptsPage.tsx`:
```tsx
onChange={(e) => {
    const checked = e.target.checked;
    setParamsEnabled((p) => ({ ...p, top: checked }));
    if (!checked) setEditState((prev) => (prev ? { ...prev, top_p: 1.0 } : null));
    //                                                          ^^^ сбрасывает на 1.0
}}
```

И в fallback-значениях:
```tsx
top_p: editState.top_p ?? 1,  // <<< дефолт 1
```

### Что нужно сделать

#### 1. Frontend: при выключении Top P — сбрасывать значение на 0

**Файл:** `frontend/src/pages/PromptsPage.tsx`

Найти обработчик checkbox'а Top P и изменить:

```tsx
// БЫЛО:
if (!checked) setEditState((prev) => (prev ? { ...prev, top_p: 1.0 } : null));

// СТАЛО:
if (!checked) setEditState((prev) => (prev ? { ...prev, top_p: 0 } : null));
```

#### 2. Frontend: дефолтное отображение 0 вместо 1 когда disabled

Найти все места где `top_p` используется с fallback `?? 1`:

```tsx
// БЫЛО:
value={editState.top_p ?? 1}
top_p: editState.top_p ?? 1,

// СТАЛО:
value={editState.top_p ?? 0}
top_p: editState.top_p ?? 0,
```

**Важно:** Это чисто визуальное изменение. Backend логика в `prompt_llm_kwargs.py` уже корректна — когда `top_p_enabled=False`, параметр `top_p` не включается в kwargs и не передаётся в OpenRouter. Менять backend не нужно.

#### 3. Frontend: normalizePrompt тоже обновить

В функции `normalizePrompt`:
```tsx
// БЫЛО:
top_p: p.top_p ?? 1,

// СТАЛО:  
top_p: p.top_p ?? 0,
```

#### 4. Frontend: PromptTestPanel передача параметров

В блоке `<PromptTestPanel>`:
```tsx
// БЫЛО:
top_p: editState.top_p ?? 1,

// СТАЛО:
top_p: editState.top_p ?? 0,
```

#### 5. Аналогично для Freq и Pres (consistency)

Проверить, что Freq и Pres при выключении тоже показывают `0` (из скриншота видно, что они уже показывают `0` — значит для них логика уже правильная). Убедиться в единообразии.

### Файлы для изменения (полный список)

| Файл                                                                              | Что менять                                                                           |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `frontend/src/pages/PromptsPage.tsx`                                              | Все `top_p ?? 1` → `top_p ?? 0`; в onChange checkbox при !checked ставить `top_p: 0` |
| `frontend/src/pages/PromptsPage.tsx` (второй инстанс, если есть дубль компонента) | То же самое                                                                          |

### НЕ менять

| Файл                                | Почему                                                                                                           |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `app/services/prompt_llm_kwargs.py` | Дефолт `1.0` в бэкенде корректен — это provider default для OpenRouter, но он не передаётся в API когда disabled |
| Модель `Prompt`                     | Дефолт в БД не влияет на API, только на отображение — фронт фиксит достаточно                                    |

---

## Чеклист для проверки после исправлений

### Баг 1 (meta_generation):
- [ ] Прогнать пайплайн для ключевого слова и проверить debug-лог: `meta_generation raw (first 500): ...`
- [ ] Убедиться, что title и description попадают в `GeneratedArticle`
- [ ] Убедиться, что на странице статьи во вкладке Metadata отображаются данные
- [ ] Проверить DOCX-экспорт — title и description в мета-таблице
- [ ] Прогнать тесты: `pytest tests/test_json_parser.py -v` (или `tests/test_pipeline.py`)

### Баг 2 (Top P):
- [ ] Открыть Prompts → выбрать любой агент → убедиться что Top P при выключенном тоггле показывает `0`
- [ ] Включить Top P → slider и input работают (диапазон 0–1)
- [ ] Выключить Top P → значение сбрасывается на `0`
- [ ] Сохранить промпт → перезагрузить страницу → Top P по-прежнему `0` при выключенном тоггле
- [ ] Запустить задачу → в логе НЕ должно быть `top_p=` если тоггл был выключен
