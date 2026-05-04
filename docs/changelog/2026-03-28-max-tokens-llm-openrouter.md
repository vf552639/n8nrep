# 28 марта 2026 — `max_tokens` в LLM (OpenRouter)

**Дата:** 2026-03-28
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема:** лимит вывода из поля **`prompts.max_tokens`** в БД не передавался в Chat Completions — провайдер использовал дефолт модели.

**Backend**
- **`app/services/llm.generate_text`**: опциональный аргумент **`max_tokens: Optional[int] = None`**; в **`client.chat.completions.create`** ключ **`max_tokens`** добавляется **только если значение не `None` и > 0** (ноль не отправляется).
- **`call_agent`** (`pipeline.py`): сборка kwargs через **`llm_sampling_kwargs_from_prompt`** — **`max_tokens`** только при **`max_tokens_enabled`** и **> 0** в записи промпта (апрель 2026).
- **`app/api/prompts.py`**: модель **`PromptTest`** — поле **`max_tokens`**; **`POST /api/prompts/test`** передаёт его в **`generate_text`**. **`PromptTestContext`** расширен overrides (в т.ч. **`max_tokens_enabled`**, **`max_tokens`**) для теста из UI без Save.

**Frontend (`PromptsPage.tsx`)**
- Панель **Model Settings**: тоггл **Max tokens**; при сохранении через **`PUT`** — **`max_tokens: null`** и **`max_tokens_enabled: false`**, если выключено (см. раздел **«Model Settings: флаги *_enabled»**).
- **Run Agent:** в **`POST /api/prompts/{id}/test`** уходят актуальные **`llm`**-поля из **`PromptTestPanel`** (включая флаги и лимит).

**Ориентиры по агентам** (настраиваются в UI, не захардкожены): `meta_generation` ~1000; аналитические структуры ~4000–8000; `primary_generation`, `improver`, `final_editing` ~16000; прочие LLM-шаги ~4000–8000.

---

**Что было сделано в последнем спринте (исторически):**
- Полностью переписан UI с использованием React, Vite, Tailwind и TanStack Query.
- Реализованы 10 вкладок управления бизнесом (Dashboard, Проекты, Задачи, Промпты, Логи и др.).
- Интегрирован real-time polling статусов задач (TanStack Query).
- Добавлена поддержка Sequential Mode для строгой очереди задач.
- Реализован SERP Data Viewer с таблицами и выгрузкой ZIP/CSV.
- Установлено управление `.env` файлом напрямую из UI SettingsPage с API.
- Встроен просмотр логов и мониторинг шагов Celery (LogsPage + StepMonitor).

**Недавние исправления (Hotfixes):**
- **Prompts (апрель 2026, task21):** булевы **`_*_enabled`** в БД и API; **`prompt_llm_kwargs`** в pipeline и тесте; UI на серверных флагах; **`syncedPromptIdRef`** для гидратации — см. раздел **«Model Settings: флаги *_enabled»** выше. **8.04.2026:** отключённые **freq/pres/top_p** не уходят в OpenRouter; см. раздел **«8 апреля 2026 — LLM…»**.
- **Prompts (3.04.2026):** **`PUT /api/prompts/{id}`** для сохранения без новой версии; стабильная гидратация по **`fullPrompt?.id`**; портал + fixed для **`ModelSelector`**; защита **`setEditState`** от **`null`** — см. раздел **3 апреля 2026** выше.
- **meta_generation + `results[]` (2.04.2026):** корректное извлечение Title/Description для `GeneratedArticle` при формате с массивом вариантов — см. раздел **2 апреля 2026**; **актуализация:** одиночный DOCX — **H1** в шапке, **Title** в мета-таблице через **`_get_all_meta_from_task`** — см. раздел **«DOCX одиночной статьи: шапка H1»** выше.
- **Tasks Form:** Восстановлена полная форма создания задачи (поля `author_id`, `additional_keywords`, `priority`).
- **Prompts UI:** Устранено дублирование (фильтр `active_only=True` на бэкенде), добавлены User-Friendly имена агентов.
- **Prompt Testing:** Синхронизировано изолированное тестирование, добавлен Backend-эндпоинт для инъекции JSON-переменных при тесте существующих промптов.
- **Task Detail / StepCard:** Промпты и переменные по шагам внутри раскрытой карточки шага (`LlmStepView`), а не отдельной вкладкой «Prompts Debug» (таб убран в пользу pipeline).
- **Article Review / Article HTML (апрель 2026):** **`PUT /api/tasks/{id}/step-result`**, Monaco на **Article Review** и единый Monaco на вкладке **html** статьи — см. раздел **«Monaco для HTML: Article Review, Article Detail»** выше.
- **Variables UI:** На странице Prompts добавлена удобная выпадающая панель со всеми (40+) переменными, разбитыми на 4 логические группы (задачи, автор, SERP, результаты). Добавлен "живой" поиск по переменным. `main_keyword` везде заменена на `keyword`.
**Что происходит сейчас:**
- Система стабильно работает в production.
- Формируется backlog для более глубоких серверных фичей (Q2 2026).
---
