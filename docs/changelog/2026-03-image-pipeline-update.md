# Март 2026 — Image pipeline (актуализация)

**Дата:** 2026-03-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

- Для выполнения image-цепочки должны быть заданы: `IMAGE_GEN_ENABLED=true`, `GOAPI_API_KEY`, `IMGBB_API_KEY`.
- Если `IMAGE_GEN_ENABLED=false`, шаги `image_prompt_generation`/`image_generation` будут корректно скипаться с логами `disabled`.
- Изменения `.env` применяются после перезапуска контейнеров `web`/`worker`.
