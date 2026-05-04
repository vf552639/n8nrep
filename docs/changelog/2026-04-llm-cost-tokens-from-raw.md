# Апрель 2026 — `llm.py`: стоимость и токены из сырого ответа OpenRouter; логи pipeline

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**`app/services/llm.py` (`generate_text`):**
- После **`chat.completions.with_raw_response.create`** тело ответа разбирается через **`json.loads(raw_response.text)`**; из **`usage`** при наличии: **`cost`** (приоритет над заголовком для денег), **`prompt_tokens`**, **`completion_tokens`**, **`total_tokens`**, а также **`prompt_tokens_details.cached_tokens`** и **`completion_tokens_details.reasoning_tokens`** (Prompt Caching / reasoning-модели).
- Если JSON не разобрался: фолбэк **`x-openrouter-cost`**, затем прежняя оценка стоимости по токенам из **`response.usage`**.
- Возврат и **`progress_callback("response_received")`** получают **`usage`** с полями **`cached_tokens`** и **`reasoning_tokens`** там, где они есть в ответе провайдера.

**`app/services/pipeline.py` (`call_agent`, `_on_llm_progress`):**
- Событие **`response_received`**: в лог задачи пишется строка **`[agent] LLM response received (P+C tokens | ⚡ N cached | 🧠 R reasoning, $…)`** — суффиксы **`cached`** / **`reasoning`** только при **> 0**; сумма в долларах с **5** знаками после запятой.

---
