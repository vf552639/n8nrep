# Май 2026 — task60: удаление проектов без FK-падений на generated_articles

## Контекст

При удалении проекта в статусе `stopped` API мог падать с `IntegrityError` и фронт показывал `Network Error`.
Причина: в `DELETE /projects/{id}` и `POST /projects/delete-selected` удалялись `tasks`, но не удалялись связанные `generated_articles`, а FK-каскада на уровне БД для этой связи нет.

## Что изменено

- **Backend (`app/api/projects.py`)**
  - Добавлен helper `_purge_project_dependents(db, project_id)`, который удаляет зависимости в безопасном порядке:
    1) `generated_articles` для задач проекта,
    2) `tasks` проекта.
  - `DELETE /projects/{id}` переведен на вызов `_purge_project_dependents(...)` перед `db.delete(project)`.
  - `POST /projects/delete-selected` также переведен на `_purge_project_dependents(...)` внутри цикла удаления.
  - Логика `force` и правила `skipped` для `pending/generating` без `force` сохранены без изменений.

## Ожидаемый эффект

- Одиночное удаление `stopped/completed/failed` проектов больше не падает на FK-ошибках.
- Bulk-удаление использует ту же безопасную последовательность удаления зависимостей.
- Поведение для проектов без статей остается прежним (удаление отрабатывает в ноль для `generated_articles`).
