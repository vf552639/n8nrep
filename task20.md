# ТЗ: Редизайн панели «Model Settings» на странице Prompts

> **Важно:** Это ТОЛЬКО визуальные изменения. Вся бизнес-логика, state management, данные и API-вызовы остаются без изменений.

---

## 0. РЕФЕРЕНС

Скриншот `111.png` — горизонтальная toolbar-панель в macOS-стиле:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ Model Settings                                                                          │
│ ┌─────────────────────┐  Max. Tokens: 20000 ●──  Temp: 0.7 ●──  Freq: 0.0 ●──  ...    │
│ │ gemini-5-flash-prev ▼│  ═══════●═══════════  ═══●═════════  ═══●═════════      [Save] │
│ └─────────────────────┘                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

Ключевые визуальные черты:
- Градиентный серый фон (как macOS toolbar)
- Заголовок «Model Settings» вверху слева мелким жирным текстом
- Под ним — ряд контролов в одну линию: dropdown модели → параметры → кнопка Save
- Каждый параметр: `Label: Value` + iOS-toggle (синяя пилюля) + slider под ними
- Кнопка Save — синяя, справа, с иконкой дискеты

---

## 1. ТЕКУЩЕЕ СОСТОЯНИЕ (что сейчас в коде)

### Файлы:
- `frontend/src/pages/PromptsPage.tsx` — панель Model Settings
- `frontend/src/components/ModelSelector.tsx` — dropdown выбора модели

### Текущий контейнер панели:
```jsx
<div className="w-full min-w-0 shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-sm">
  <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
    ...
  </div>
</div>
```

### Текущие элементы внутри (слева направо):
1. **Model** — label "Model" + `<ModelSelector>` (w-[280px])
2. **Max tokens** — label + checkbox + number input (w-[160px])
3. **Temperature** — label + checkbox "Custom" + range slider + number input (w-[180px])
4. **Freq. Penalty** — label + checkbox + number input (w-[160px])
5. **Pres. Penalty** — label + checkbox + number input (w-[160px])
6. **Top P** — label + checkbox + number input (w-[140px])
7. **Save** — emerald кнопка с dirty-indicator, `ml-auto`

### Текущий ModelSelector (`ModelSelector.tsx`):
- Кнопка: белый фон, border, эмодзи 🤖 + имя модели + ChevronDown
- По клику: dropdown с полем поиска (Search) наверху + список моделей с фильтрацией
- Данные: из `orModels` (хук `useQuery(["openrouter-models"])` → `GET /settings/openrouter-models`)
- При выборе: `onChange(model)` → `setEditState({ ...prev, model: m })`
- Закрытие: по клику вне (через `useRef` + `mousedown` listener)

### State для параметров (из `PromptsPage`):
```typescript
const [paramsEnabled, setParamsEnabled] = useState({
  maxTokens: false,
  temp: false,
  freq: false,
  pres: false,
  top: false,
});
```
Инициализируется через `paramsEnabledFromPrompt()`:
- maxTokens: `true` если `max_tokens != null && max_tokens > 0`
- temp: `true` если `temperature !== 1.0`
- freq: `true` если `frequency_penalty !== 0.0`
- pres: `true` если `presence_penalty !== 0.0`
- top: `true` если `top_p !== 1.0`

Когда toggle **выключен** → параметр сбрасывается в дефолт:
- maxTokens OFF → `max_tokens = null`
- temp OFF → `temperature = 1.0`
- freq OFF → `frequency_penalty = 0.0`
- pres OFF → `presence_penalty = 0.0`
- top OFF → `top_p = 1.0`

---

## 2. ЧТО НУЖНО СДЕЛАТЬ

### 2.1. Создать компонент `ToggleSwitch`

**Файл:** `frontend/src/components/ToggleSwitch.tsx`

**Props:**
```typescript
interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}
```

**Визуал (точно по скриншоту — iOS-стиль):**
- Общая форма: горизонтальная пилюля (capsule/pill)
- Размер: ширина **36px**, высота **20px**
- Скругление: полностью круглый (`rounded-full`)
- **Включён (checked=true):**
  - Фон пилюли: `#3B82F6` (Tailwind `bg-blue-500`)
  - Белый кружок (thumb): диаметр **16px**, сдвинут вправо (отступ 2px от правого края)
- **Выключен (checked=false):**
  - Фон пилюли: `#CBD5E1` (Tailwind `bg-slate-300`)
  - Белый кружок (thumb): диаметр **16px**, сдвинут влево (отступ 2px от левого края)
- Кружок: `bg-white`, `rounded-full`, мини-тень `shadow-sm`
- Анимация перемещения кружка: `transition-transform duration-200 ease-in-out`
- При `disabled`: `opacity-50`, `cursor-not-allowed`, клик не работает
- Реализация: `<button>` с внутренним `<span>` для кружка. Позиционирование через `translate-x`.

**Пример реализации (ориентир для разработчика):**
```tsx
<button
  type="button"
  role="switch"
  aria-checked={checked}
  onClick={() => !disabled && onChange(!checked)}
  className={`
    relative inline-flex h-5 w-9 shrink-0 items-center rounded-full
    transition-colors duration-200 ease-in-out
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2
    ${checked ? 'bg-blue-500' : 'bg-slate-300'}
    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
  `}
>
  <span
    className={`
      pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm
      transform transition-transform duration-200 ease-in-out
      ${checked ? 'translate-x-4' : 'translate-x-0.5'}
    `}
  />
</button>
```

---

### 2.2. Изменить контейнер панели Model Settings

**Файл:** `PromptsPage.tsx` — блок `{activePromptListInfo && editState && !isLoadingPrompt && (...)}`

**Было (внешний div):**
```
rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-sm
```

**Стало:**
```
rounded-xl border border-slate-300/80 shadow-md
bg-gradient-to-b from-[#e8ebef] to-[#d5d9df]
px-4 py-2.5
```

Разбивка:
- `bg-gradient-to-b from-[#e8ebef] to-[#d5d9df]` — лёгкий вертикальный градиент как на скриншоте (светло-серый сверху → чуть темнее снизу), имитирует macOS toolbar
- `border border-slate-300/80` — тонкий бордер, слегка прозрачный
- `rounded-xl` — мягкие скругления (12px)
- `shadow-md` — умеренная тень (глубже чем сейчас)
- Внутренний padding: `px-4 py-2.5`

**Внутренняя структура — ДВЕ строки:**

```
Строка 1: заголовок "Model Settings"
Строка 2: [dropdown модели] [Max.Tokens: val ●] [Temp: val ● ═══] [Freq: val ● ═══] [Pres: val ● ═══] [TopP: val ● ═══] [Save]
```

```jsx
<div className="rounded-xl border border-slate-300/80 shadow-md bg-gradient-to-b from-[#e8ebef] to-[#d5d9df] px-4 py-2.5">
  {/* Строка 1: заголовок */}
  <div className="text-[13px] font-semibold text-slate-700 mb-2">Model Settings</div>
  
  {/* Строка 2: все контролы в одну линию */}
  <div className="flex items-center gap-5 overflow-x-auto">
    {/* Dropdown модели */}
    {/* Параметры */}
    {/* Кнопка Save */}
  </div>
</div>
```

**Ключевое отличие от текущего:**
- Был `flex-wrap` → стало `flex-nowrap` (через `overflow-x-auto`), элементы НИКОГДА не переносятся на новую строку
- Заголовок «Model Settings» — отдельная строка сверху, мелким текстом
- Контролы выстроены строго горизонтально

---

### 2.3. Селектор модели (левый блок)

**Файл:** `ModelSelector.tsx` + использование в `PromptsPage.tsx`

**Изменения в `ModelSelector.tsx`:**

Кнопка (закрытое состояние — то, что видно постоянно):
- **Убрать** эмодзи 🤖 — чистый текст
- Стиль кнопки:
  ```
  bg-white border border-slate-300 rounded-lg px-3 py-[7px]
  text-[13px] font-medium text-slate-800 font-mono
  shadow-inner (или shadow-sm)
  hover:border-slate-400
  ```
- Ширина: `min-w-[220px] max-w-[260px]`
- Текст модели: `truncate` (обрезать длинные имена)
- Иконка ChevronDown: `w-4 h-4 text-slate-400 shrink-0` — справа

Dropdown (открытое состояние — появляется при клике):
- Всё оставить как есть функционально
- Визуальные правки:
  - `rounded-xl` (вместо `rounded-lg`)
  - `shadow-xl` (глубже)
  - `border-slate-300`
  - Поисковый input: без изменений (уже хорошо выглядит)

**В PromptsPage.tsx — вызов компонента:**
```jsx
<div className="shrink-0">
  <ModelSelector
    className="w-[240px]"
    value={editState.model || "openai/gpt-4o"}
    models={orModels || ["openai/gpt-4o"]}
    onChange={(m) => setEditState((prev) => (prev ? { ...prev, model: m } : null))}
  />
</div>
```

**Функционал НЕ менять:**
- Список моделей из `orModels` (OpenRouter API)
- Фильтрация по поиску
- Клик вне → закрытие
- Выбор → `onChange` → обновление `editState.model`

---

### 2.4. Каждый параметр (Max Tokens, Temperature, Freq., Pres., Top P)

Каждый параметр — это **один вертикальный блок** фиксированной ширины. Все 5 блоков стоят в ряд.

**Общая структура одного блока параметра:**
```
┌─────────────────────┐
│ Label: Value    ●── │   ← верхняя строка: label + числовое значение + ToggleSwitch
│ ═══════●═══════════ │   ← нижняя строка: slider (только если toggle ON)
└─────────────────────┘
```

**Верхняя строка (label + value + toggle):**
```jsx
<div className="flex items-center gap-1.5">
  <span className="text-[12px] font-semibold text-slate-600 whitespace-nowrap">
    Max. Tokens:
  </span>
  <input
    type="number"
    value={...}
    className="w-[70px] text-[12px] font-semibold font-mono text-slate-800
               bg-transparent border-none outline-none text-right
               disabled:text-slate-400"
    disabled={!paramsEnabled.maxTokens}
  />
  <ToggleSwitch
    checked={paramsEnabled.maxTokens}
    onChange={(checked) => { ... }}
  />
</div>
```

Детали:
- **Label:** `text-[12px] font-semibold text-slate-600` — сокращённые имена:
  - `Max. Tokens:` (с точкой, двоеточием)
  - `Temperature:` (полное слово)
  - `Freq.:` (сокращённо)
  - `Pres.:` (сокращённо)
  - `Top P:` (без точки после P)
- **Value (числовой input):** стилизован «как текст» — без видимого бордера, прозрачный фон. Редактируемый. По фокусу можно добавить `focus:ring-1 focus:ring-blue-400 focus:rounded`
  - Ширина: `w-[70px]` для всех, кроме Max Tokens: `w-[80px]` (числа бывают 5–6 цифр)
  - Шрифт: `font-mono font-semibold text-[12px]`
  - Когда toggle OFF: `text-slate-400` (серый текст)
- **Toggle:** компонент `ToggleSwitch` (см. п. 2.1), стоит справа от значения

**Нижняя строка (slider):**
```jsx
{paramsEnabled.temp && (
  <input
    type="range"
    min={0} max={2} step={0.1}
    value={editState.temperature ?? 0.7}
    onChange={...}
    className="w-full h-[6px] mt-1 accent-blue-500 cursor-pointer"
  />
)}
```

Детали:
- Slider показывается **ТОЛЬКО** когда toggle включён
- Когда toggle выключен — slider скрыт, блок становится компактнее (однострочный)
- Стилизация range slider:
  - Высота трека: 6px
  - Цвет заполненной части: синий (через `accent-blue-500` или кастомный CSS)
  - Цвет незаполненной части: `bg-blue-200`
  - Thumb (ползунок): белый кружок с синим бордером, диаметр ~14px
  - `mt-1` — маленький отступ от верхней строки

**Особенность Max Tokens:**
- Slider НЕ показывать (диапазон 1–200000 не подходит для slider)
- Только числовой ввод + toggle. Блок компактнее остальных.

**Ширины блоков:**
| Параметр    | Ширина блока |
| ----------- | ------------ |
| Max Tokens  | `w-[170px]`  |
| Temperature | `w-[170px]`  |
| Freq.       | `w-[145px]`  |
| Pres.       | `w-[145px]`  |
| Top P       | `w-[135px]`  |

**Диапазоны слайдеров (без изменений — как в текущем коде):**
| Параметр      | min | max | step |
| ------------- | --- | --- | ---- |
| Temperature   | 0   | 2   | 0.1  |
| Freq. Penalty | -2  | 2   | 0.1  |
| Pres. Penalty | -2  | 2   | 0.1  |
| Top P         | 0   | 1   | 0.1  |

---

### 2.5. Кнопка Save

**Было:** `bg-emerald-600`, текст "Save" / "Save"

**Стало:**
```jsx
<button
  onClick={() => saveMutation.mutate(editState)}
  disabled={saveMutation.isPending || !isDirty}
  className="
    relative ml-auto shrink-0
    inline-flex items-center gap-1.5
    bg-blue-600 hover:bg-blue-700 text-white
    rounded-lg px-4 py-[7px]
    text-[13px] font-medium
    shadow-sm
    disabled:opacity-50 disabled:cursor-not-allowed
    transition-colors
  "
>
  {isDirty && (
    <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-amber-400 ring-2 ring-white" />
  )}
  <Save className="h-4 w-4" />
  Save
</button>
```

Изменения:
- Цвет: `blue-600` вместо `emerald-600` (как на скриншоте)
- Скругление: `rounded-lg`
- Иконка дискеты (`Save` из lucide) + текст «Save»
- Позиция: `ml-auto` (прижата к правому краю панели)
- Dirty-индикатор: жёлто-оранжевая точка (как сейчас, но `bg-amber-400`, чуть крупнее: `h-2.5 w-2.5`)

---

### 2.6. Кастомная стилизация range slider (CSS)

Дефолтные range inputs выглядят по-разному в браузерах. Для соответствия скриншоту добавить CSS.

**Файл:** добавить в `frontend/src/index.css` (или глобальный CSS):

```css
/* Custom range slider styling for Model Settings */
input[type="range"].model-slider {
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  background: #bfdbfe; /* blue-200 */
  outline: none;
}

input[type="range"].model-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: white;
  border: 2px solid #3b82f6; /* blue-500 */
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  cursor: pointer;
}

input[type="range"].model-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: white;
  border: 2px solid #3b82f6;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  cursor: pointer;
}

input[type="range"].model-slider:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
```

Добавить класс `model-slider` к каждому `<input type="range">` в панели.

---

## 3. ПОЛНАЯ ИТОГОВАЯ СХЕМА JSX (псевдокод)

```jsx
{activePromptListInfo && editState && !isLoadingPrompt && (
  <div className="shrink-0 rounded-xl border border-slate-300/80 shadow-md bg-gradient-to-b from-[#e8ebef] to-[#d5d9df] px-4 py-2.5">
    
    {/* Заголовок */}
    <div className="text-[13px] font-semibold text-slate-700 mb-2">
      Model Settings
    </div>

    {/* Контролы — одна горизонтальная линия */}
    <div className="flex items-start gap-5 overflow-x-auto pb-1">
      
      {/* 1. Dropdown модели */}
      <div className="shrink-0">
        <ModelSelector ... />
      </div>

      {/* 2. Max Tokens */}
      <div className="shrink-0 w-[170px]">
        <div className="flex items-center gap-1.5">
          <span className="text-[12px] font-semibold text-slate-600 whitespace-nowrap">Max. Tokens:</span>
          <input type="number" ... />
          <ToggleSwitch checked={paramsEnabled.maxTokens} onChange={...} />
        </div>
        {/* БЕЗ slider для Max Tokens */}
      </div>

      {/* 3. Temperature */}
      <div className="shrink-0 w-[170px]">
        <div className="flex items-center gap-1.5">
          <span>Temperature:</span>
          <input type="number" ... />
          <ToggleSwitch checked={paramsEnabled.temp} onChange={...} />
        </div>
        {paramsEnabled.temp && (
          <input type="range" className="model-slider w-full mt-1" min={0} max={2} step={0.1} ... />
        )}
      </div>

      {/* 4. Freq. */}
      <div className="shrink-0 w-[145px]">
        <div className="flex items-center gap-1.5">
          <span>Freq.:</span>
          <input type="number" ... />
          <ToggleSwitch checked={paramsEnabled.freq} onChange={...} />
        </div>
        {paramsEnabled.freq && (
          <input type="range" className="model-slider w-full mt-1" min={-2} max={2} step={0.1} ... />
        )}
      </div>

      {/* 5. Pres. */}
      <div className="shrink-0 w-[145px]">
        <div className="flex items-center gap-1.5">
          <span>Pres.:</span>
          <input type="number" ... />
          <ToggleSwitch checked={paramsEnabled.pres} onChange={...} />
        </div>
        {paramsEnabled.pres && (
          <input type="range" className="model-slider w-full mt-1" min={-2} max={2} step={0.1} ... />
        )}
      </div>

      {/* 6. Top P */}
      <div className="shrink-0 w-[135px]">
        <div className="flex items-center gap-1.5">
          <span>Top P:</span>
          <input type="number" ... />
          <ToggleSwitch checked={paramsEnabled.top} onChange={...} />
        </div>
        {paramsEnabled.top && (
          <input type="range" className="model-slider w-full mt-1" min={0} max={1} step={0.1} ... />
        )}
      </div>

      {/* 7. Save */}
      <button className="ml-auto shrink-0 bg-blue-600 ..." ...>
        <Save /> Save
      </button>

    </div>
  </div>
)}
```

---

## 4. ЧТО НЕ ТРОГАТЬ (КРИТИЧНО)

| Что                                                       | Почему                                   |
| --------------------------------------------------------- | ---------------------------------------- |
| `paramsEnabled` state и его логика                        | Определяет какие параметры активны       |
| `paramsEnabledFromPrompt()`                               | Инициализация при переключении промптов  |
| `isPromptDirty()`                                         | Определяет показывать ли dirty-indicator |
| `normalizePrompt()`                                       | Нормализация для сравнений               |
| `buildCleanPromptFromServer()`                            | Инициализация editState                  |
| `saveMutation`                                            | Сохранение на бэкенд                     |
| `editState` и все `setEditState` вызовы                   | Локальное состояние формы                |
| OpenRouter API запрос (`useQuery(["openrouter-models"])`) | Источник списка моделей                  |
| Version menu, skip_in_pipeline чекбокс                    | Находятся вне панели Model Settings      |
| System Prompt / User Prompt editors                       | Ниже панели                              |
| Test panel                                                | Ниже панели                              |
| Variables drawer                                          | Боковая панель                           |
| Левая панель со списком агентов                           | Отдельный блок                           |

---

## 5. ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

| Файл                                        | Действие                                                         |
| ------------------------------------------- | ---------------------------------------------------------------- |
| `frontend/src/components/ToggleSwitch.tsx`  | **СОЗДАТЬ**                                                      |
| `frontend/src/components/ModelSelector.tsx` | **ИЗМЕНИТЬ** (убрать 🤖, обновить стили кнопки и dropdown)        |
| `frontend/src/pages/PromptsPage.tsx`        | **ИЗМЕНИТЬ** (секция Model Settings — контейнер + все параметры) |
| `frontend/src/index.css` (или аналог)       | **ДОБАВИТЬ** CSS для кастомного range slider                     |

---

## 6. ЧЕКЛИСТ ПРОВЕРКИ

- [ ] Панель — горизонтальная полоса с градиентным фоном
- [ ] Заголовок "Model Settings" мелким текстом сверху
- [ ] Все контролы в ОДНУ линию, без переносов (`overflow-x-auto` для узких экранов)
- [ ] ModelSelector: без эмодзи, moно-шрифт, macOS-стиль кнопки
- [ ] ModelSelector: dropdown с поиском работает (данные с OpenRouter)
- [ ] Все 5 параметров: `Label: Value` + ToggleSwitch + slider
- [ ] Max Tokens: только числовой ввод (без slider)
- [ ] Toggle ON → slider появляется, значение редактируемо
- [ ] Toggle OFF → slider скрыт, значение серое, input disabled
- [ ] Slider стилизован (кастомный CSS: синий трек, белый thumb с синим border)
- [ ] Кнопка Save: синяя (blue-600), с иконкой дискеты
- [ ] Dirty indicator (жёлтая точка) работает
- [ ] Переключение между промптами в левой панели корректно обновляет ВСЕ значения
- [ ] При save → данные уходят на бэкенд корректно (проверить через Network tab)
- [ ] Ничего не пропало: version menu, skip_in_pipeline, editors, test panel, variables
