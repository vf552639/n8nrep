# Май 2026 — task55: Blueprints/Legal visibility + editable clustering preview

**Контекст:** в форме проекта были два UX-блока:
- для legal-страниц пользователю было сложно понять, что реально сохранено в `blueprint_pages.page_type`;
- после `Cluster Keywords` распределение показывалось read-only, без возможности удалить шумные ключи и переназначить их между страницами.

**Сделано**
- **`frontend/src/pages/BlueprintsPage.tsx`**
  - в таблице страниц blueprint для колонки **Type** добавлен бейдж с **сырым `page_type` из БД** (monospace), рядом с человекочитаемым label;
  - в `CreateBlueprintModal` / `AddBlueprintPageModal` / `EditBlueprintPageModal` / delete page в `onError` теперь показывается деталь backend-ошибки через `formatApiErrorDetail(...)`, а не только общий текст.
- **`frontend/src/pages/ProjectsPage.tsx`**
  - добавлен локальный компонент **`KeywordChip`** для assigned и unassigned ключей:
    - hover-действие **`×`** (удаление из текущего кластера),
    - клик по чипу открывает меню перемещения в любую страницу blueprint или в **Unassigned**;
  - добавлены чистые хелперы **`removeKeyword(state, kw, fromSlug)`** и **`moveKeyword(state, kw, fromSlug, toSlug)`** с корректным пересчётом `total_assigned`;
  - отключён пункт перемещения в текущую же секцию (no-op);
  - добавлена поясняющая заметка: изменения применяются только к текущему результату кластеризации, повторный кластеринг использует исходный список из textarea.

**Проверка и диагностика**
- Диагностический SQL по `site_blueprints/blueprint_pages` из task55 не выполнился в подключённом MCP `user-supabase`, т.к. там отсутствуют таблицы проекта (подключена другая БД). Для финальной проверки кейса с `responsible_gambling` нужен доступ к рабочей БД проекта.
- Локальная статическая проверка окружения частично ограничена:
  - `npm run lint` — отсутствует `@typescript-eslint/eslint-plugin` в текущем окружении;
  - `npm run typecheck` — runtime Node слишком старый для текущего TypeScript (`Unexpected token ?` в `_tsc.js`).
- IDE-диагностика по изменённым файлам ошибок не показала.
