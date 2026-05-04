# Апрель 2026 — task47: аудит step-классов (без правок кода)

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Артефакт**
- Добавлен отчёт `task46-audit.md` в корне репозитория (snapshot-аудит A–G).

**Ключевые выводы аудита**
- Регистрация шагов: `STEP_REGISTRY` содержит 21/21 шага; для всех пресетов (`full/category/about/legal`) `missing=[]`.
- Ограничение по размеру: все `steps/*.py` <= 400 LOC.
- Выявлен P0-риск: `retryable_errors=(LLMError,)` объявлен во многих шагах, но `LLMError` фактически не бросается в текущем call-path (`llm_client`), из-за чего retry-policy для LLM-шагов по сути «мёртвая».
- Выявлены P1/P2-зоны: raw `Exception/ValueError` в pipeline-слое, default-policy в `image_*`, низкая adoption `ctx.*` геттеров, неоднозначные `ctx.db.commit()` внутри ряда шагов.

**Открыто после аудита**
- Это осознанно только документационный шаг; исправления P0/P1/P2 идут отдельными PR по action-items из `task46-audit.md`.

---
