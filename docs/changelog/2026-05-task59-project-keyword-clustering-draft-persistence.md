# Май 2026 — task59 (UI): стабильность Cluster Keywords в черновиках проектов

## Контекст

В `CreateProjectModal` проявлялись два связанных дефекта:

1. Кластеризация исчезала после повторного открытия сохраненного черновика, хотя `project_keywords.clustered` в БД был сохранен.
2. На больших списках ключей (около 90) результат кластеризации часто был пустым или неочевидным для пользователя.

## Что изменено

- **Frontend (`frontend/src/pages/ProjectsPage.tsx`)**
  - Удален `useEffect`, который очищал `clusterResult` по изменениям `additional_keywords_raw` и `blueprint_id` и мог срабатывать после программного `setFormData(...)` при загрузке draft.
  - Очистка кластеризации перенесена в user-driven `onChange`:
    - select `Blueprint`,
    - textarea `Additional Keywords`.
  - В хендлерах используются functional updates `setFormData(prev => ...)`, чтобы избежать stale closure.
  - В `clusterMutation.onSuccess` добавлен явный `toast.error`, если `total_assigned === 0 && total_keywords > 0`.

- **Backend (`app/services/keyword_clusterer.py`)**
  - `max_tokens` увеличен с `4000` до `8000`.
  - Добавлен `logger.info(...)` с диагностикой:
    - `total_keywords`,
    - `total_assigned`,
    - `unassigned`,
    - `response_length`,
    - `model`.

## Ожидаемый эффект

- При редактировании черновика ранее сохраненный preview кластеризации не затирается на втором рендере.
- Кластеризация очищается только при реальном ручном изменении входных данных.
- Для больших списков ключей возрастает шанс получить распределение; если распределение пустое, пользователь видит явную ошибку и может скорректировать ввод.
