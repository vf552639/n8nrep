# Март–апрель 2026 — обновления (стабильность `html_structure`, промпты, UI)

**Дата:** 2026-03-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Шаг `html_structure` (снижение потери контента, `app/services/pipeline.py`):**
- В **`call_agent`** kwargs для **`generate_text`** собираются через **`llm_sampling_kwargs_from_prompt`**: **`max_tokens`** попадает в запрос только при **`max_tokens_enabled`** и **значении > 0** в строке промпта; в **`llm.generate_text`** ключ добавляется только при **> 0** (иначе максимум модели на стороне OpenRouter). **Актуализация 8.04.2026:** **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** в HTTP-запросе только при соответствующих **`_*_enabled`**.
- При потере слов **> 7%** — один **recovery**-вызов LLM с усиленным контекстом; при **> 20%** после этого — **`programmatic_html_insert`** (`app/services/html_inserter.py`): плейсхолдер `{{content}}` или контейнеры `main` / `article` / `#content` / типичные `div.content` и др.
- **`config`:** `SELF_CHECK_MAX_RETRIES`, `SELF_CHECK_MAX_COST_PER_STEP` — бюджет ретраев для exclude-слов и логика recovery.
- **`call_agent_with_exclude_validation`:** учёт бюджета ретраев по exclude-словам.
- Агент факт-чека контента в пайплайне: **`content_fact_checking`**; в **`get_prompt_obj`** добавлен fallback на устаревшее имя **`fact_checking`** в БД.
- **`scripts/seed_prompts.py`:** для `html_structure` рекомендуется **`google/gemini-2.5-flash`**, **`max_tokens` 16000**, пониженная температура, блок **CRITICAL RULE** про сохранение всего текста; рекомендуемые **`max_tokens`** по остальным агентам в seed; принудительное обновление части промптов через **`PROMPTS_FORCE_UPDATE`**.

**Санитизация промптов и Monaco:**
- **`app/api/prompts.py`:** **`_sanitize()`** — замена U+2028/U+2029, NBSP, BOM при **создании** и **restore** промпта.
- **`scripts/fix_prompt_line_terminators.py`** — одноразовая очистка всех записей в таблице `prompts`.
- **`PromptsPage.tsx`:** Monaco **`unusualLineTerminators: "off"`** на редакторах и панели теста.

**Model Settings (PromptsPage, март–апрель 2026):**
- **Актуализация (апрель 2026, task21):** полное описание — раздел **«Model Settings: флаги *_enabled»** в начале файла (**`_*_enabled`** в БД, **`paramsEnabledFromPrompt`**, **`isPromptDirty`**, **`syncedPromptIdRef`**, **`PUT`** с флагами). Ниже — эволюция до явных флагов.
- **`paramsEnabled`:** `{ maxTokens, temp, freq, pres, top }` — **Max tokens** по умолчанию выключен (в БД **`null`** при отключении); при включении — значение из БД или **4000**.
- Синхронизация с сервером: **`useEffect`** с **`[derivedActiveId, fullPrompt?.id]`** + **`syncedPromptIdRef`** (см. актуальный раздел выше).
- **`saveMutation`:** **`updateInPlace`** / **`PUT`**; при выключенном Max tokens — **`max_tokens: null`**, **`max_tokens_enabled: false`**; **`isPromptDirty`** учитывает все пять тогглов.
- Селектор модели: фиксированная ширина **280px**, **`truncate`** внутри **`ModelSelector`**; ряд параметров с **`flex-wrap`** и фиксированными ширинами блоков (модель 280px, Max tokens 160px, Temperature 180px, Freq./Pres. 160px, Top P 140px).
- Кнопка **Test** убрана из Model Settings; **Test** в шапке карточки агента (рядом с Variables на узком экране). **Save** остаётся в Model Settings.
