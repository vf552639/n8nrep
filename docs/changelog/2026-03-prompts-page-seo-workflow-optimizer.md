# Март 2026 — страница Prompts («SEO Workflow Optimizer») и API

**Дата:** 2026-03-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Цель:** единая рабочая область для редактирования промптов агентов пайплайна с тестом LLM, переменными и версиями.

**Backend (`app/api/prompts.py`, `app/services/llm.py`, `app/services/pipeline.py`):**
- `GET /api/prompts` — список промптов; `GET /api/prompts/{id}` — полная карточка (system/user, модель, параметры, `skip_in_pipeline`, версия).
- `POST /api/prompts/` — upsert (сохранение черновика, создание новой версии по логике сервиса).
- `POST /api/prompts/test` — тест без привязки к id (если используется).
- `POST /api/prompts/{prompt_id}/test` — тест существующего промпта с подстановкой контекста (JSON переменных); в ответе — вывод LLM, usage/cost при наличии, **`resolved_prompts`** (итоговые system/user после шаблонизации).
- `GET /api/prompts/{id}/versions` — история версий; `POST /api/prompts/{id}/versions/{source_prompt_id}/restore` — восстановить версию (новая активная запись).
- В **`llm.generate_text`** учитываются usage/cost из OpenRouter: приоритет сырой JSON **`usage`** (**`cost`**, cached/reasoning tokens), затем заголовки и оценка — см. раздел **«`llm.py`: стоимость и токены из сырого ответа»** в начале файла.

**Frontend (`frontend/src/pages/PromptsPage.tsx` и связанные):**
- Заголовок страницы: **SEO Workflow Optimizer** (`text-xl font-bold text-slate-900`), над панелью Model Settings.
- **Model Settings:** белая панель (`bg-white`, рамка `slate-200`). Модель через **`ModelSelector`** (список с `GET /api/settings/openrouter-models`). **Max tokens** — чекбокс + число (по умолчанию выключено → `null` в БД; подробности — раздел **«Model Settings (март–апрель 2026)»** ниже и **`max_tokens`** от 28.03.2026). Параметры: чекбокс + **range + number** для **Temperature**; для **Freq. / Pres. / Top P** — чекбокс + **number**. При «выключенном» Temperature в сохранение уходит **`temperature: 1.0`**. Кнопка **Save** в Model Settings; **Test** — в шапке агента. Тест передаёт эффективный **`max_tokens`** в **`POST /api/prompts/{id}/test`**.
- **Skip in pipeline** вынесен из Model Settings в **шапку выбранного агента** (чекбокс рядом с версией / мобильной кнопкой Variables).
- **Сайдбар агентов:** светлый список (белый фон, рамка), выбранный пункт — голубая подсветка (`bg-blue-50`, левая граница). Индикаторы точек: синяя — выбранный агент; серая — `skip_in_pipeline`; зелёная — остальные активные.
- **Редакторы:** только **вертикальный** стек: System Prompt сверху, User Prompt снизу; Monaco **`theme="vs"`** (светлая тема); заголовки секций `bg-slate-50`, без тёмных панелей.
- **Variable Explorer:** поиск, группы переменных; в строке — `{{name}}` и иконка **Copy** (описание в `title`/tooltip, без drag-handle `GripVertical` в списке); drag с строки для вставки в Monaco по-прежнему можно оставить через `draggable`.
- **Тест:** нижняя панель по кнопке Test с вкладками (контекст / результат / resolved prompts); поведение сохранено, стили в общей светлой гамме.
- **Версии:** компактный бейдж `v{N}` с выпадающим списком и **Restore**.
- **Save без отката/перескока:** после `POST /api/prompts/` UI использует ответ `{ id, version }` и переключает `activePromptId` на новый `id` перед инвалидацией кэша. Это убирает визуальный откат на старую версию и fallback на первый агент после обновления списка.

**Layout:** `MainLayout` для `pathname === "/prompts"` не рендерит **`Header`**, main — `bg-slate-100 p-0`, чтобы страница промптов использовала всю высоту под кастомный layout.

**Инструменты:** локальный `npm run build` / `tsc` требуют **Node 18+** (на старых Node, например 12, падает сам TypeScript).

---
