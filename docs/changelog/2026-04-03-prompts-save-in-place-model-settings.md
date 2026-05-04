# 3 апреля 2026 — Prompts: сохранение in-place, Model Settings UI, фикс выбора модели

**Дата:** 2026-04-03
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Backend (`app/api/prompts.py`)**
- **`PUT /api/prompts/{prompt_id}`** — обновление **той же** строки в БД без новой версии и нового UUID; ответ в формате **`GET /{prompt_id}`** (в т.ч. **`updated_at`**), общая сериализация через **`_prompt_to_response()`**.
- Обычное сохранение из UI идёт через **`PUT`**, а не через **`POST /`** (который создаёт новую версию агента).

**Frontend (`frontend/src/api/prompts.ts`, `PromptsPage.tsx`)**
- **`promptsApi.updateInPlace(id, payload)`** → **`PUT /prompts/{id}`**; **`saveMutation`** использует его; после успеха — **`setQueryData(['prompt', id])`**, инвалидация **`['prompts']`**.
- **Гидрация `editState` / `paramsEnabled`:** `useEffect` зависит от **`[derivedActiveId, fullPrompt?.id]`**, а не от ссылки на объект **`fullPrompt`**, чтобы refetch React Query с тем же id **не сбрасывал** локальные правки (в т.ч. выбранную модель). Убран **`justSavedRef`**. **Актуализация (апрель 2026):** гидратация через **`syncedPromptIdRef`** — см. раздел **«Model Settings: флаги *_enabled»** выше.
- Во всех **`setEditState`** при отсутствии `prev` возвращается **`prev`**, а не **`null`**, чтобы не обнулять форму.

**Редизайн Model Settings (визуал, `task20`)**
- Панель: градиент **`bg-gradient-to-b from-[#e8ebef] to-[#d5d9df]`**, заголовок **Model Settings**, один горизонтальный ряд с **`overflow-x-auto`**, **`ToggleSwitch`** (iOS-стиль) для Max. Tokens / Temperature / Freq. / Pres. / Top P, слайдеры с классом **`model-slider`** (кастомный CSS в **`frontend/src/index.css`**), кнопка **Save** — **`bg-blue-600`** с dirty-индикатором.
- Компонент **`frontend/src/components/ToggleSwitch.tsx`**.

**`ModelSelector` и баг «пропали параметры»**
- Выпадающий список рендерится через **`createPortal(..., document.body)`** с **`position: fixed`** по координатам кнопки (обновление на scroll/resize). Иначе родитель с **`overflow-x-auto`** обрезал по вертикали соседние блоки параметров и выпадашку; визуально оставались заголовок и поле **Search models...**.
- Клик вне: учитываются и кнопка, и портальное меню.

---
