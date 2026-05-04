# Апрель 2026 — Model Settings: флаги `*_enabled` (task21), pipeline и гидратация UI

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема (закрыта):** тогглы Max tokens / Temperature / Freq. / Pres. / Top P «угадывались» по числовым значениям; **`isDirty`** и сохранение расходились с ожиданиями; при refetch React Query форма могла рассинхронизироваться.

**База данных и модель**
- Таблица **`prompts`**: колонки **`max_tokens_enabled`**, **`temperature_enabled`**, **`frequency_penalty_enabled`**, **`presence_penalty_enabled`**, **`top_p_enabled`** (boolean, не nullable). Миграция **`k5m6n7o8p9qb_add_prompt_param_enabled_flags`**: после добавления колонок выполняется **`UPDATE`** — начальные значения флагов выводятся из числовых полей (например, **`temperature_enabled`** если **`|temperature - 0.7| > ε`**).
- Одноразовый скрипт повторной синхронизации флагов: **`scripts/migrate_param_flags.py`** (идемпотентный SQL, на случай расхождения после деплоя).

**Backend**
- **`app/services/prompt_llm_kwargs.py`** — **`llm_sampling_kwargs_from_prompt()`**: кастомные **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** и **`max_tokens`** попадают в вызов LLM только при соответствующем **`_*_enabled`**; **`temperature`** всегда (**0.7** при выключенном тоггле). **Актуализация 8.04.2026:** при **`false`** для freq/pres/top_p ключи **не включаются** в запрос к OpenRouter (см. раздел **«8 апреля 2026 — LLM: не передавать…»** выше). Тот же helper с optional overrides используется в **`POST /api/prompts/{id}/test`**.
- **`app/services/pipeline.py`** — **`call_agent`** собирает kwargs через helper; в лог задачи пишется строка **`[agent] LLM params: …`** (**`format_llm_params_log_line`** — только фактически переданные sampling-поля).
- **`app/api/prompts.py`** — **`PromptUpdate`** и **`_prompt_to_response`** включают все **`_*_enabled`**; **`PromptTestContext`** расширен полями для передачи несохранённых параметров из UI при тесте.

**Frontend (`frontend/src/pages/PromptsPage.tsx`)**
- **`paramsEnabledFromPrompt(p)`** — только с серверных **`p.*_enabled`**, без эвристик по числам.
- **`isPromptDirty`** — сравнение всех пяти тогглов с сохранённым промптом и значений только для включённых параметров.
- **`saveMutation`** — **`promptsApi.updateInPlace`** с телом **`_*_enabled`** и значениями по правилам task21.
- **`PromptTestPanel`** — проп **`llm: PromptTestLlmOptions`** (модель + флаги + числа); тест шлёт актуальное состояние формы без обязательного Save.
- **Гидратация:** **`useRef` `syncedPromptIdRef`** — при первом появлении данных для **`fullPrompt.id`** один раз вызываются **`setEditState(buildCleanPromptFromServer(fullPrompt))`** и **`setParamsEnabled(paramsEnabledFromPrompt(fullPrompt))`**; при повторном refetch с **тем же** id локальные правки **не** затираются (нет антипаттерна «флаг внутри **`setEditState`**»). Зависимости эффекта: **`[derivedActiveId, fullPrompt?.id]`**.

**Деплой (напоминание)**
- Сервисы **`web` / `worker` / `beat`** в **`docker-compose`** монтируют **`.:/app`** — Python берётся с **хоста**; после **`git pull`** достаточно перезапуска, образ пересобирать не обязательно (кроме смены **`requirements.txt`**).
- **`frontend`** собирается **в образе** — после смены TS/React нужны **`docker compose build --no-cache frontend`** и **`alembic upgrade head`** на БД.
- Браузер: жёсткое обновление / отключение кэша, чтобы не подтягивался старый **`dist`**.

---
