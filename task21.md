Сейчас разберусь в архитектуре проекта, чтобы понять корень проблемы.Теперь я вижу полную картину. Проблема ясна — здесь несколько связанных багов в коде. Давай сделаю ТЗ.Теперь у меня полная картина. Вижу **две версии кода** в проекте (дублирование из task20 и текущий код) и несколько критических багов. Составляю детальное ТЗ.Теперь у меня полная картина. Создаю детальное ТЗ.

---

# ТЗ: Исправление сохранения и применения Model Settings на странице Prompts

## 0. ОПИСАНИЕ ПРОБЛЕМЫ

**Симптомы (со скриншотов и описания пользователя):**

1. Заходим на страницу Prompts → видим Model Settings с `Max. Tokens: default`, `Temperature: 1`, `Freq.: 0`, `Pres.: 0`, `Top P: 1` — **все тогглы выключены** (скриншот 1).
2. Включаем тоггл Temperature → значение меняется на `0.7` → **кнопка Save остаётся неактивной** (скриншот 2). То есть `isDirty` возвращает `false`, хотя пользователь явно изменил параметр.
3. При обновлении страницы — состояние сбрасывается к скриншоту 1. Данные не сохранились.
4. Высока вероятность, что при генерации контента параметры тоже используются неправильно (всегда дефолты).

## 1. КОРНЕВЫЕ ПРИЧИНЫ (анализ кода)

### Баг 1: Логика `paramsEnabledFromPrompt()` — тоггл Temperature почти никогда не включается

```typescript
function paramsEnabledFromPrompt(p: Prompt) {
  return {
    temp: (p.temperature ?? 0.7) !== 1.0,  // ← ПРОБЛЕМА
    ...
  };
}
```

**Проблема:** Если в БД `temperature = 0.7` (дефолт для большинства промптов, плюс скрипт `fix_prompt_defaults.py` ставит 0.7), то `0.7 !== 1.0` → `true` → тоггл включён. Но если temperature = `1.0` (дефолт API), то тоггл выключен. **Это нелогично:** пользователь видит тоггл выключенным при `1.0`, но в БД реально хранится `1.0`, и `saveMutation` при `temp=OFF` отправляет `1.0`. Получается замкнутый круг — **нет разницы между "не задано" и "задано 1.0"**.

Для Temperature это ещё терпимо, но настоящая проблема глубже — в коде есть **две разные версии** `paramsEnabled`, `isPromptDirty`, и `saveMutation`, и непонятно, какая из них реально работает в продакшене.

### Баг 2: Дублирование кода — две конфликтующие реализации

В project knowledge видно **два варианта кода** в `PromptsPage.tsx`:

**Вариант А** (старый, без `maxTokens` и `temp` в paramsEnabled):
```typescript
const [paramsEnabled, setParamsEnabled] = useState({ freq: false, pres: false, top: false });
// нет maxTokens, нет temp
```

**Вариант Б** (новый, из task20):
```typescript
const [paramsEnabled, setParamsEnabled] = useState({
  maxTokens: false, temp: false, freq: false, pres: false, top: false
});
```

Если в продакшене работает **Вариант А** — тогда temperature **всегда** отправляется как `data.temperature ?? 0.7` (hardcoded), тоггл для неё вообще не управляет ничем. Max Tokens тоже не управляется тогглом.

### Баг 3: `isDirty` не считает включение/выключение тоггла Temperature за изменение

В варианте А `isPromptDirty()`:
```typescript
if (e.temperature !== s.temperature) return true;
```
Здесь нет проверки `params.temp` вообще, потому что `temp` не входит в `paramsEnabled`. Значит если пользователь включает тоггл Temperature и slider показывает `0.7`, а в БД тоже `0.7` — **isDirty = false**, кнопка Save неактивна. Именно то, что на скриншоте 2.

В варианте Б (из task20) проверка есть:
```typescript
const savedTempOn = (saved.temperature ?? 0.7) !== 1.0;
if (params.temp !== savedTempOn) return true;
```
Но если этот вариант не применён...

### Баг 4: `saveMutation` — Temperature ВСЕГДА отправляется, даже когда тоггл выключен

В варианте А:
```typescript
temperature: data.temperature ?? 0.7,
```
Нет проверки `paramsEnabled.temp`. Temperature всегда уходит как `editState.temperature`, а не сбрасывается в дефолт при выключенном тоггле.

### Баг 5: В БД нет явного признака "параметр кастомизирован"

Бэкенд хранит `temperature: Float, default=0.7`. Нет булева флага типа `temperature_custom: bool`. Фронтенд определяет "включён/выключен" по значению: `temperature !== 1.0` → включён. Но `1.0` — это не "дефолт API", это "дефолт при выключенном тоггле". А `0.7` — это дефолт промпта. Путаница полная.

### Баг 6: При генерации контента pipeline берёт значения прямо из БД

```python
# pipeline.py
kwargs = {
    "temperature": prompt.temperature,
    "frequency_penalty": prompt.frequency_penalty,
    ...
}
```

Если в БД `temperature = 0.7` (потому что Save никогда не срабатывал с правильным значением, или тоггл не работает) — pipeline всегда использует `0.7`, даже если пользователь хотел `0.3`.

## 2. ЧТО НУЖНО СДЕЛАТЬ

### 2.1. Бэкенд: Добавить явные флаги кастомизации параметров

**Файл:** `app/models/prompt.py`

Добавить 5 новых полей:
```python
max_tokens_enabled = Column(Boolean, default=False, nullable=False, server_default='false')
temperature_enabled = Column(Boolean, default=False, nullable=False, server_default='false')
frequency_penalty_enabled = Column(Boolean, default=False, nullable=False, server_default='false')
presence_penalty_enabled = Column(Boolean, default=False, nullable=False, server_default='false')
top_p_enabled = Column(Boolean, default=False, nullable=False, server_default='false')
```

**Смысл:** Теперь фронтенд НЕ гадает по значению, включён параметр или нет. Флаг хранится явно в БД. Если `temperature_enabled = false` — pipeline использует дефолт OpenRouter (не передаёт параметр вообще). Если `true` — берёт значение из `temperature`.

**Миграция Alembic:**
```
alembic revision --autogenerate -m "add_param_enabled_flags"
```

Логика миграции для существующих данных:
- `max_tokens_enabled = True` если `max_tokens IS NOT NULL AND max_tokens > 0`
- `temperature_enabled = True` если `temperature IS NOT NULL AND temperature != 0.7` (считаем 0.7 дефолтом, который не был кастомизирован явно)
- `frequency_penalty_enabled = True` если `frequency_penalty IS NOT NULL AND frequency_penalty != 0.0`
- `presence_penalty_enabled = True` если `presence_penalty IS NOT NULL AND presence_penalty != 0.0`
- `top_p_enabled = True` если `top_p IS NOT NULL AND top_p != 1.0`

### 2.2. Бэкенд: Обновить API эндпоинты

**Файл:** `app/api/prompts.py`

**2.2.1. `PromptUpdate` (Pydantic модель):**
```python
class PromptUpdate(BaseModel):
    system_prompt: str
    user_prompt: str = ""
    model: str
    max_tokens: Optional[int] = None
    max_tokens_enabled: bool = False
    temperature: Optional[float] = 0.7
    temperature_enabled: bool = False
    frequency_penalty: Optional[float] = 0.0
    frequency_penalty_enabled: bool = False
    presence_penalty: Optional[float] = 0.0
    presence_penalty_enabled: bool = False
    top_p: Optional[float] = 1.0
    top_p_enabled: bool = False
    skip_in_pipeline: bool = False
```

**2.2.2. `update_prompt_in_place` (PUT):**
Добавить сохранение новых полей:
```python
prompt.max_tokens_enabled = body.max_tokens_enabled
prompt.temperature_enabled = body.temperature_enabled
prompt.frequency_penalty_enabled = body.frequency_penalty_enabled
prompt.presence_penalty_enabled = body.presence_penalty_enabled
prompt.top_p_enabled = body.top_p_enabled
```

**2.2.3. `_prompt_to_response`:**
Добавить в ответ:
```python
"max_tokens_enabled": prompt.max_tokens_enabled or False,
"temperature_enabled": prompt.temperature_enabled or False,
"frequency_penalty_enabled": prompt.frequency_penalty_enabled or False,
"presence_penalty_enabled": prompt.presence_penalty_enabled or False,
"top_p_enabled": prompt.top_p_enabled or False,
```

**2.2.4. `GET /prompts` (список):**
Без изменений — он возвращает краткую инфу, флаги не нужны.

### 2.3. Бэкенд: Обновить Pipeline

**Файл:** `app/services/pipeline.py`, функция `call_agent`

Заменить текущую жёсткую передачу параметров:
```python
kwargs = {
    "system_prompt": system_text,
    "user_prompt": user_msg,
    "model": prompt.model,
}

# Передаём параметры ТОЛЬКО если они явно включены
if prompt.temperature_enabled and prompt.temperature is not None:
    kwargs["temperature"] = prompt.temperature
else:
    kwargs["temperature"] = 0.7  # дефолт OpenRouter

if prompt.frequency_penalty_enabled and prompt.frequency_penalty is not None:
    kwargs["frequency_penalty"] = prompt.frequency_penalty
else:
    kwargs["frequency_penalty"] = 0.0

if prompt.presence_penalty_enabled and prompt.presence_penalty is not None:
    kwargs["presence_penalty"] = prompt.presence_penalty
else:
    kwargs["presence_penalty"] = 0.0

if prompt.top_p_enabled and prompt.top_p is not None:
    kwargs["top_p"] = prompt.top_p
else:
    kwargs["top_p"] = 1.0

if prompt.max_tokens_enabled and prompt.max_tokens is not None and prompt.max_tokens > 0:
    kwargs["max_tokens"] = prompt.max_tokens
```

**Важно:** Добавить в лог параметры с флагами, чтобы было видно, что реально отправлено в LLM:
```python
add_log(
    ctx.db, ctx.task,
    f"[{agent_name}] LLM params: model={prompt.model}, "
    f"temp={'%.1f' % kwargs.get('temperature', 0.7)} ({'custom' if prompt.temperature_enabled else 'default'}), "
    f"max_tokens={kwargs.get('max_tokens', 'auto')}, "
    f"freq={kwargs.get('frequency_penalty', 0.0)}, pres={kwargs.get('presence_penalty', 0.0)}, "
    f"top_p={kwargs.get('top_p', 1.0)}",
    level="info", step=agent_name,
)
```

### 2.4. Фронтенд: Типы

**Файл:** `frontend/src/types/prompt.ts`

Добавить поля в интерфейс `Prompt`:
```typescript
max_tokens_enabled?: boolean;
temperature_enabled?: boolean;
frequency_penalty_enabled?: boolean;
presence_penalty_enabled?: boolean;
top_p_enabled?: boolean;
```

### 2.5. Фронтенд: API клиент

**Файл:** `frontend/src/api/prompts.ts`

Обновить тип данных в `updateInPlace`:
```typescript
updateInPlace: (
    id: string,
    data: {
      system_prompt: string;
      user_prompt: string;
      model: string;
      max_tokens?: number | null;
      max_tokens_enabled: boolean;
      temperature: number;
      temperature_enabled: boolean;
      frequency_penalty?: number;
      frequency_penalty_enabled: boolean;
      presence_penalty?: number;
      presence_penalty_enabled: boolean;
      top_p?: number;
      top_p_enabled: boolean;
      skip_in_pipeline: boolean;
    }
  ) => api.put<Prompt>(`/prompts/${id}`, data).then((res) => res.data),
```

### 2.6. Фронтенд: PromptsPage.tsx — полный рефакторинг Model Settings логики

**Файл:** `frontend/src/pages/PromptsPage.tsx`

**2.6.1. `paramsEnabled` — инициализация из сервера:**

```typescript
const [paramsEnabled, setParamsEnabled] = useState({
  maxTokens: false,
  temp: false,
  freq: false,
  pres: false,
  top: false,
});
```

Функция `paramsEnabledFromPrompt` — ПОЛНОСТЬЮ ЗАМЕНИТЬ:
```typescript
function paramsEnabledFromPrompt(p: Prompt) {
  return {
    maxTokens: !!p.max_tokens_enabled,
    temp: !!p.temperature_enabled,
    freq: !!p.frequency_penalty_enabled,
    pres: !!p.presence_penalty_enabled,
    top: !!p.top_p_enabled,
  };
}
```

Больше никакого угадывания по значению. Берём булев флаг прямо с сервера.

**2.6.2. `isPromptDirty` — ПОЛНОСТЬЮ ЗАМЕНИТЬ:**

```typescript
function isPromptDirty(
  edit: Partial<Prompt> | null,
  saved: Prompt | null | undefined,
  params: { maxTokens: boolean; temp: boolean; freq: boolean; pres: boolean; top: boolean }
): boolean {
  if (!edit || !saved) return false;

  // Текстовые поля
  if ((edit.system_prompt ?? "") !== (saved.system_prompt ?? "")) return true;
  if ((edit.user_prompt ?? "") !== (saved.user_prompt ?? "")) return true;
  if ((edit.model ?? "") !== (saved.model ?? "")) return true;
  if (!!edit.skip_in_pipeline !== !!saved.skip_in_pipeline) return true;

  // Проверяем каждый тоггл: изменился ли сам тоггл?
  const savedParams = paramsEnabledFromPrompt(saved as Prompt);
  if (params.maxTokens !== savedParams.maxTokens) return true;
  if (params.temp !== savedParams.temp) return true;
  if (params.freq !== savedParams.freq) return true;
  if (params.pres !== savedParams.pres) return true;
  if (params.top !== savedParams.top) return true;

  // Если тоггл включён — проверяем изменилось ли значение
  if (params.maxTokens) {
    if ((edit.max_tokens ?? null) !== (saved.max_tokens ?? null)) return true;
  }
  if (params.temp) {
    const editVal = Math.round((edit.temperature ?? 0.7) * 10) / 10;
    const savedVal = Math.round((saved.temperature ?? 0.7) * 10) / 10;
    if (editVal !== savedVal) return true;
  }
  if (params.freq) {
    const editVal = Math.round((edit.frequency_penalty ?? 0) * 10) / 10;
    const savedVal = Math.round((saved.frequency_penalty ?? 0) * 10) / 10;
    if (editVal !== savedVal) return true;
  }
  if (params.pres) {
    const editVal = Math.round((edit.presence_penalty ?? 0) * 10) / 10;
    const savedVal = Math.round((saved.presence_penalty ?? 0) * 10) / 10;
    if (editVal !== savedVal) return true;
  }
  if (params.top) {
    const editVal = Math.round((edit.top_p ?? 1) * 10) / 10;
    const savedVal = Math.round((saved.top_p ?? 1) * 10) / 10;
    if (editVal !== savedVal) return true;
  }

  return false;
}
```

**2.6.3. `saveMutation` — ПОЛНОСТЬЮ ЗАМЕНИТЬ mutationFn:**

```typescript
mutationFn: (data: Partial<Prompt>) => {
  if (!data.id) throw new Error("Missing prompt id");
  return promptsApi.updateInPlace(data.id, {
    system_prompt: data.system_prompt ?? "",
    user_prompt: data.user_prompt ?? "",
    model: data.model ?? "",
    
    max_tokens: paramsEnabled.maxTokens ? (data.max_tokens ?? null) : null,
    max_tokens_enabled: paramsEnabled.maxTokens,
    
    temperature: paramsEnabled.temp ? (data.temperature ?? 0.7) : 0.7,
    temperature_enabled: paramsEnabled.temp,
    
    frequency_penalty: paramsEnabled.freq ? (data.frequency_penalty ?? 0.0) : 0.0,
    frequency_penalty_enabled: paramsEnabled.freq,
    
    presence_penalty: paramsEnabled.pres ? (data.presence_penalty ?? 0.0) : 0.0,
    presence_penalty_enabled: paramsEnabled.pres,
    
    top_p: paramsEnabled.top ? (data.top_p ?? 1.0) : 1.0,
    top_p_enabled: paramsEnabled.top,
    
    skip_in_pipeline: !!data.skip_in_pipeline,
  });
},
```

**2.6.4. UI тогглов — обработчик onChange:**

Когда пользователь включает/выключает тоггл, нужно:
1. Обновить `paramsEnabled`
2. НЕ менять `editState` (значение параметра остаётся как было — просто флаг меняется)
3. `isDirty` автоматически пересчитается, потому что `paramsEnabled` входит в зависимости `useMemo`

Пример для Temperature:
```tsx
<ToggleSwitch
  checked={paramsEnabled.temp}
  onChange={(checked) => {
    setParamsEnabled((p) => ({ ...p, temp: checked }));
    // Если включаем — восстановить значение из editState (оно уже там)
    // Если выключаем — НЕ обнулять editState.temperature, 
    //   просто при Save отправится дефолт
  }}
/>
```

### 2.7. Фронтенд: Обновить тест промпта

**Файл:** `frontend/src/pages/PromptsPage.tsx` (или где вызывается `testPrompt`)

При тестировании промпта тоже нужно передавать актуальные параметры. Сейчас `testPrompt` по id берёт параметры из БД. Но если пользователь изменил temperature в UI и ещё не сохранил — тест пойдёт со старыми параметрами.

**Вариант решения:** Передавать параметры в тестовый запрос из `editState`:
```typescript
// В POST /prompts/{id}/test добавить optional overrides
{
  context: testContext,
  model: editState.model,
  max_tokens: paramsEnabled.maxTokens ? editState.max_tokens : null,
  temperature: paramsEnabled.temp ? editState.temperature : undefined,
  frequency_penalty: paramsEnabled.freq ? editState.frequency_penalty : undefined,
  presence_penalty: paramsEnabled.pres ? editState.presence_penalty : undefined,
  top_p: paramsEnabled.top ? editState.top_p : undefined,
}
```

На бэкенде в `PromptTestContext` добавить optional поля для override:
```python
class PromptTestContext(BaseModel):
    context: Dict[str, Any]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    top_p: Optional[float] = None
```

В эндпоинте `test_prompt_by_id` — использовать override если передан, иначе из prompt:
```python
temp = test_ctx.temperature if test_ctx.temperature is not None else prompt.temperature
```

### 2.8. Скрипт миграции данных

**Файл:** `scripts/migrate_param_flags.py`

Одноразовый скрипт, который для всех существующих промптов проставит `*_enabled` флаги по текущим значениям:
```python
for p in prompts:
    p.max_tokens_enabled = p.max_tokens is not None and p.max_tokens > 0
    p.temperature_enabled = p.temperature is not None and p.temperature != 0.7
    p.frequency_penalty_enabled = p.frequency_penalty is not None and p.frequency_penalty != 0.0
    p.presence_penalty_enabled = p.presence_penalty is not None and p.presence_penalty != 0.0
    p.top_p_enabled = p.top_p is not None and p.top_p != 1.0
```

**Запускать ДО деплоя нового фронтенда.**

## 3. ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

| Файл                                      | Действие                                                                                                             |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `app/models/prompt.py`                    | ИЗМЕНИТЬ — добавить 5 полей `*_enabled`                                                                              |
| `alembic/versions/xxx_add_param_flags.py` | СОЗДАТЬ — миграция БД                                                                                                |
| `app/api/prompts.py`                      | ИЗМЕНИТЬ — `PromptUpdate`, `PromptTestContext`, `update_prompt_in_place`, `_prompt_to_response`, `test_prompt_by_id` |
| `app/services/pipeline.py`                | ИЗМЕНИТЬ — `call_agent` (использование `*_enabled` флагов)                                                           |
| `frontend/src/types/prompt.ts`            | ИЗМЕНИТЬ — добавить 5 полей                                                                                          |
| `frontend/src/api/prompts.ts`             | ИЗМЕНИТЬ — типы в `updateInPlace`                                                                                    |
| `frontend/src/pages/PromptsPage.tsx`      | ИЗМЕНИТЬ — `paramsEnabledFromPrompt`, `isPromptDirty`, `saveMutation`, hydration useEffect                           |
| `scripts/migrate_param_flags.py`          | СОЗДАТЬ — одноразовая миграция данных                                                                                |

## 4. ЧТО НЕ ТРОГАТЬ

- Визуал Model Settings (тогглы, слайдеры, layout) — уже сделан в task20, не ломать
- `ModelSelector.tsx` — не связан с этим багом
- Логика версионирования промптов
- Левая панель агентов
- System/User Prompt editors
- Variable Explorer

## 5. ПОРЯДОК ВЫПОЛНЕНИЯ

1. **Alembic миграция** — добавить колонки `*_enabled` с дефолтом `false`
2. **Скрипт миграции данных** — проставить флаги по текущим значениям
3. **Бэкенд: модель + API** — обновить Pydantic модели, эндпоинты PUT и GET/{id}
4. **Бэкенд: pipeline** — обновить `call_agent`
5. **Фронтенд: типы + API клиент**
6. **Фронтенд: PromptsPage логика** — `paramsEnabledFromPrompt`, `isPromptDirty`, `saveMutation`
7. **Фронтенд: тест промпта** — передавать overrides

## 6. КАК ПРОВЕРИТЬ ЧТО ВСЁ РАБОТАЕТ

**Тест-кейс 1: Toggle → Save → Reload**
1. Открыть промпт, у которого temperature = 0.7 в БД
2. Тоггл Temperature должен отображаться согласно `temperature_enabled` (скорее всего OFF после миграции)
3. Включить тоггл → поставить 0.3 → кнопка Save должна стать активной (isDirty = true)
4. Нажать Save → toast "Saved"
5. Обновить страницу → Temperature = 0.3, тоггл включён

**Тест-кейс 2: Toggle OFF → Save → Reload**
1. У промпта temperature_enabled = true, temperature = 0.5
2. Выключить тоггл Temperature → Save должен стать активным
3. Нажать Save
4. Обновить → тоггл выключен, значение показывает дефолт (0.7 серым)
5. В БД: `temperature = 0.7, temperature_enabled = false`

**Тест-кейс 3: Pipeline использует правильные параметры**
1. Для промпта `ai_structure_analysis` поставить temperature = 0.3, включить тоггл, сохранить
2. Запустить задачу
3. В логах задачи должно быть: `LLM params: temp=0.3 (custom)`

**Тест-кейс 4: Тест промпта с несохранёнными параметрами**
1. Открыть промпт, поменять temperature на 0.1 (не сохраняя)
2. Нажать Test
3. Тест должен использовать temperature = 0.1 (из UI), а не из БД
