# Апрель 2026 — Monaco для HTML: Article Review, Article Detail; ручное сохранение `step_results`

**Дата:** 2026-04-01
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Backend (`app/api/tasks.py`):**
- **`PUT /api/tasks/{task_id}/step-result`** — тело **`{ "step_name": "<ключ шага из ALL_STEPS>", "result": "<html или текст>" }`**. Шаг должен существовать в **`task.step_results`** со **`status: "completed"`**. Обновляется **`result`**, выставляются **`manually_edited: true`**, **`edited_at`**, пересчитывается **`output_word_count`** (**`count_content_words`**). Предыдущий объект шага добавляется в **`{step_name}_prev_versions`** (как при **rerun**). Ответ **`{"status": "ok"}`**. Для мутации JSONB используется **`flag_modified`**.

**Frontend (`frontend/src/api/tasks.ts`):**
- **`tasksApi.updateStepResult(taskId, stepName, result)`** → **`PUT`** выше.

**`TaskDetailPage.tsx` — вкладка 📝 Article Review:**
- Контент для превью/редактора: **самый «поздний» завершённый шаг** из цепочки **`final_editing` → `improver` → `interlinking_citations` → `reader_opinion` → `competitor_comparison` → `primary_generation` → `primary_generation_about` → `primary_generation_legal`**; бейдж **`Showing: <step>`**, для шагов **`primary_generation*`** дописывается **`(draft)`** где применимо (см. **`TaskDetailPage`**).
- Вкладка доступна, если есть такой шаг **или** активен **test mode** (**`waiting_for_approval`**).
- **Preview** — **iframe** **`srcDoc`** (как раньше). **Source** — **Monaco** (**`@monaco-editor/react`**, `language="html"`, **`vs-dark`**, word wrap, minimap): по умолчанию **read-only**, кнопки **Edit** / **Read only** и **Save** (сохранение в выбранный шаг через **`updateStepResult`** + инвалидация **`task`** / **`task-steps`**).

**`ArticleDetailPage.tsx` — вкладка `html`:**
- Один экземпляр **Monaco**: **`readOnly: !editingHtml`**, значение **`full_page_html || html_content`** в режиме просмотра и **`htmlDraft`** при правке; кнопки **Edit HTML** / **Save** / **Cancel** и **`PATCH /api/articles/{id}`** без изменения контракта.

---
