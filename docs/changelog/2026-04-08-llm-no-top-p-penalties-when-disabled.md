# 8 апреля 2026 — LLM: не передавать `top_p` / penalties в API при `*_enabled = False`; Force Fail/Complete для `stale`

**Дата:** 2026-04-08
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема (закрыта):** при выключенных тогглах в запрос всё равно уходили **`top_p=1.0`**, **`frequency_penalty=0`**, **`presence_penalty=0`** — часть моделей на OpenRouter ведёт себя иначе, чем при полном отсутствии ключей в теле запроса.

**Backend**
- **`app/services/prompt_llm_kwargs.py`** — **`llm_sampling_kwargs_from_prompt()`**: в словаре для **`generate_text`** всегда есть **`temperature`** (при выключенном тоггле — **0.7**); **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** добавляются **только** если соответствующий **`_*_enabled`**; **`max_tokens`** — по-прежнему только при enabled и **> 0**. **`format_llm_params_log_line`**: в строку лога попадают **freq** / **pres** / **top_p** только если они реально переданы в вызов API (суффикс **`(custom)`**).
- **`app/services/llm.py`** — **`generate_text`**: аргументы **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** — **`Optional[float] = None`**; в **`client.chat.completions.create`** ключи добавляются только при **`is not None`**.
- **`app/api/prompts.py`** — в **`PromptTest`** для сухого **`POST /api/prompts/test`** поля **`frequency_penalty`**, **`presence_penalty`**, **`top_p`** по умолчанию **`None`**, чтобы не дублировать старое поведение «всегда 0 / 1.0» без явной передачи с клиента.

**Задачи (`app/api/tasks.py`)**
- **`POST /api/tasks/{id}/force-status`** (**`complete` | `fail`**): разрешены статусы **`processing`** и **`stale`** (раньше только **`processing`**). Для **`pending`**, **`completed`**, **`failed`** и др. — **400** с текстом **`Only 'processing' or 'stale' tasks can be forced`**. **Актуализация 13.04.2026:** также **`paused`** (SERP URL review) — см. раздел **«13 апреля 2026»** ниже.

**Тесты:** **`tests/test_prompt_llm_kwargs.py`** — отсутствие отключённых ключей в kwargs и обновлённые проверки лога.

---
