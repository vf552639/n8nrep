# Drafts for "Add Project" modal

## Context

Сейчас на вкладке Project попап «Add Project» имеет только два сценария: «Start Project» (полная валидация → запись в БД со статусом `pending` → постановка задачи в Celery) и «Cancel». Пользователю нужна возможность сохранять промежуточное состояние формы как черновик и возвращаться к нему позже, дозаполнять поля и только потом запускать проект.

Бэкенд — FastAPI + SQLAlchemy, фронтенд — React Query. Никакого draft‑механизма для проектов в коде пока нет (есть `draft_step.py`, но это про генерацию контента, к проектам не относится). Существующий статус‑enum: `pending | generating | awaiting_page_approval | completed | failed | stopped`.

Решения, согласованные с пользователем:
- **Минимум для черновика** — только `name`. Все остальные поля опциональны.
- **Размещение** — черновики в общем списке проектов с визуальным бейджем `Draft`, доступны через фильтр статуса.
- **Открытие** — клик по строке черновика открывает тот же попап в режиме редактирования с предзаполненными полями. Запуск — кнопкой `Launch Project` в футере.

## Подход (сводка)

1. Добавить статус `"draft"` (в коде, без alembic enum-миграции — поле `status` уже `String(50)`).
2. Сделать `blueprint_id`, `site_id`, `seed_keyword`, `country`, `language` nullable в `site_projects` (alembic-миграция), чтобы можно было сохранить черновик с одним только `name`.
3. Бэкенд: 3 новых эндпоинта (`POST /projects/draft`, `PATCH /projects/{id}`, `POST /projects/{id}/launch`) + правка существующих хендлеров для корректной работы с draft-статусом.
4. Фронтенд: расширить `CreateProjectModal` режимом `edit-draft`, добавить кнопку «Save Draft» в футер, отрисовать бейдж и сделать строку черновика кликабельной для редактирования.

## Backend

### 1. Alembic-миграция
Новый файл в [alembic/versions/](alembic/versions/) (по образцу [y1z2a3b4c5d6_blueprint_page_hide_author_geo.py](alembic/versions/y1z2a3b4c5d6_blueprint_page_hide_author_geo.py)).

`upgrade()`:
```python
op.alter_column("site_projects", "blueprint_id", existing_type=postgresql.UUID(), nullable=True)
op.alter_column("site_projects", "site_id", existing_type=postgresql.UUID(), nullable=True)
op.alter_column("site_projects", "seed_keyword", existing_type=sa.String(500), nullable=True)
op.alter_column("site_projects", "country", existing_type=sa.String(10), nullable=True)
op.alter_column("site_projects", "language", existing_type=sa.String(10), nullable=True)
```
`downgrade()` — обратное (с заметкой, что откат сломается, если в таблице остались строки с null’ами).

### 2. SQLAlchemy-модель
[app/models/project.py:11-75](app/models/project.py) — снять `nullable=False` с `blueprint_id` (16), `site_id` (17), `seed_keyword` (18), `country` (19), `language` (20). В `comment` поля `status` (24-27) дописать `| draft`.

### 3. Pydantic-схемы
[app/schemas/project.py](app/schemas/project.py) — добавить:

```python
class SiteProjectDraftCreate(BaseModel):
    name: str
    blueprint_id: str | None = None
    seed_keyword: str | None = None
    seed_is_brand: bool = False
    target_site: str | None = None
    country: str | None = None
    language: str | None = None
    author_id: int | None = None
    serp_config: dict[str, Any] | None = None
    project_keywords: dict[str, Any] | None = None
    legal_template_map: dict[str, str] | None = None
    use_site_template: bool = True
    competitor_urls: list[str] | None = None

    # Аналогичные validator'ы для competitor_urls / target_site / country (country — только если не None)


class SiteProjectUpdate(BaseModel):
    # Все поля опциональны — PATCH
    name: str | None = None
    blueprint_id: str | None = None
    seed_keyword: str | None = None
    seed_is_brand: bool | None = None
    target_site: str | None = None
    country: str | None = None
    language: str | None = None
    author_id: int | None = None
    serp_config: dict[str, Any] | None = None
    project_keywords: dict[str, Any] | None = None
    legal_template_map: dict[str, str] | None = None
    use_site_template: bool | None = None
    competitor_urls: list[str] | None = None
    # validator’ы по образцу SiteProjectCloneBody
```

В `SiteProjectResponse` (145-158): сделать `blueprint_id`, `site_id`, `seed_keyword` опциональными (`str | None`) — это покрывает draft-строки.

### 4. Эндпоинты в [app/api/projects.py](app/api/projects.py)

**Новый `POST /projects/draft`:**
```python
@router.post("/draft")
def create_draft(payload: SiteProjectDraftCreate, db: Session = Depends(get_db)):
    new_p = SiteProject(
        name=payload.name,
        blueprint_id=payload.blueprint_id or None,  # UUID-каст, если задан
        site_id=None,  # site резолвится только при launch
        seed_keyword=payload.seed_keyword,
        country=(payload.country or None),
        language=(payload.language or None),
        author_id=payload.author_id,
        seed_is_brand=payload.seed_is_brand,
        status="draft",
        serp_config=payload.serp_config or {},
        project_keywords=payload.project_keywords,
        legal_template_map=payload.legal_template_map,  # без _validate_legal_template_map — отложим до launch
        use_site_template=bool(payload.use_site_template),
        competitor_urls=list(payload.competitor_urls or []),
    )
    db.add(new_p); db.commit(); db.refresh(new_p)
    return {"id": str(new_p.id), "status": "draft"}
```
Никаких duplicate-check, SERP-resolve, Celery-вызовов.

**Новый `PATCH /projects/{id}`:**
```python
@router.patch("/{id}")
def update_project(id: str, payload: SiteProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project: raise HTTPException(404, "Project not found")
    if project.status != "draft":
        raise HTTPException(400, "Only drafts can be edited")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(project, k, v)
    db.commit(); db.refresh(project)
    return {"id": str(project.id), "status": project.status}
```
Никакого `_resolve_site_or_markup_only` здесь — `site_id` остаётся пустым до запуска.

**Новый `POST /projects/{id}/launch`:**
Логика повторяет «вторую половину» [create_project()](app/api/projects.py:529-646), но работает с уже существующей строкой:
```python
@router.post("/{id}/launch")
def launch_draft(id: str, db: Session = Depends(get_db)):
    project = db.query(SiteProject).filter(SiteProject.id == id).first()
    if not project: raise HTTPException(404, "Project not found")
    if project.status != "draft":
        raise HTTPException(400, f"Only drafts can be launched (current: {project.status})")
    # 1. валидация полного набора обязательных полей: name/blueprint_id/seed_keyword/country/language
    # 2. blueprint = db.query(SiteBlueprint).filter(...).first(); 404 если нет
    # 3. site, effective_use_site_template = _resolve_site_or_markup_only(...)
    # 4. duplicate-check (как в create_project)
    # 5. _validate_serp_config / _validate_legal_template_map / лимит project_keywords
    # 6. auto-assign author по country+language если author_id пустой
    # 7. project.site_id = site.id; project.use_site_template = ...; project.status = "pending"
    # 8. db.commit()
    # 9. _ensure_worker_available(); result = process_site_project.delay(str(project.id))
    # 10. project.celery_task_id = result.id; db.commit()
    return {"id": str(project.id), "status": "Project queued", "celery_task_id": result.id}
```

**Правки существующих хендлеров:**
- [create_project()](app/api/projects.py:551) — заменить `SiteProject.status.not_in(["failed"])` на `SiteProject.status.not_in(["failed", "draft"])`, чтобы черновик не блокировал создание реального проекта с теми же параметрами.
- [start_project()](app/api/projects.py:1033-1042) — оставить как есть (требует `status == "pending"`); черновики должны идти через `/launch`. Сообщение об ошибке уже понятное.
- [delete_project()](app/api/projects.py:1067-1086) — добавить `draft` к статусам, при которых force не нужен (черновики удаляются свободно, как `completed`/`failed`). Сейчас блокируются только `pending|generating`, поэтому `draft` уже проходит — менять не нужно. **Уточнение: проверить, что Celery-revoke не вызывается зря; для draft `celery_task_id` всегда null, так что `_revoke_project_celery_task(None)` должен быть no-op (проверить).**
- [STATUS_OPTIONS на фронте](frontend/src/pages/ProjectsPage.tsx:62-69) и фильтр `status` в [list_projects()](app/api/projects.py:272) — никаких изменений не требуется, фильтр и так пропускает любую строку.

### 5. Frontend API
[frontend/src/api/projects.ts](frontend/src/api/projects.ts) — добавить:
```ts
saveDraft: (data: SiteProjectDraftPayload) =>
  api.post<{ id: string; status: string }>("/projects/draft", data, { skipErrorToast: true }),

updateDraft: (id: string, data: SiteProjectUpdatePayload) =>
  api.patch<{ id: string; status: string }>(`/projects/${id}`, data, { skipErrorToast: true }),

launchDraft: (id: string) =>
  api.post<{ id: string; status: string; celery_task_id: string }>(
    `/projects/${id}/launch`, {}, { skipErrorToast: true }),
```
Типы `SiteProjectDraftPayload` (все поля кроме `name` — optional) и `SiteProjectUpdatePayload` (все optional) описать рядом с существующим `SiteProjectCreatePayload` (10-39).

## Frontend — модалка

[frontend/src/pages/ProjectsPage.tsx:546-1416](frontend/src/pages/ProjectsPage.tsx)

1. **Параметризация модалки.** Расширить пропсы `CreateProjectModal`:
   ```ts
   type ModalMode = "create" | "edit-draft";
   props: { isOpen; onClose; mode: ModalMode; draftProject?: ProjectListItem }
   ```
   Если `mode === "edit-draft"`, `formData` инициализируется из `draftProject`.

2. **Mutations внутри модалки** (рядом с уже существующим `mutation` на 758-778):
   - `saveDraftMutation` — для `mode==="create"` шлёт `projectsApi.saveDraft(data)`, для `mode==="edit-draft"` — `projectsApi.updateDraft(draftProject.id, data)`. На успехе: toast `"Draft saved"`, инвалидация `["projects"]`, `onClose()`.
   - `launchMutation` — `projectsApi.launchDraft(draftProject.id)`. На успехе: toast `"Project launched"`, инвалидация, `onClose()`.

3. **handleSubmit (781-798)** — извлечь общий «полная валидация» в функцию `validateRequired(formData) → string | null`. Использовать:
   - в существующем create-flow («Start Project») — как сейчас;
   - в `launchMutation` — перед вызовом `/launch`.
   - в `saveDraftMutation` — **не использовать**, draft принимает любые поля.

4. **Футер модалки (1387-1411).** Сделать условным от `mode`:
   - `create`: `[Cancel] [Save Draft] [Preview] [Start Project]`
   - `edit-draft`: `[Cancel] [Save Draft] [Preview] [Launch Project]`
   - Кнопка `Save Draft` всегда disabled только если `formData.name` пустое (минимальное требование) и/или одна из мутаций pending.
   - `Start Project` / `Launch Project` — `disabled={mutation.isPending || launchMutation.isPending || saveDraftMutation.isPending}`.

5. **Заголовок** на 862 — динамически: `mode==="edit-draft" ? "Edit Draft" : "Create Generative Project"`.

## Frontend — список проектов

[frontend/src/pages/ProjectsPage.tsx](frontend/src/pages/ProjectsPage.tsx)

1. **STATUS_OPTIONS (62-69)** — добавить `{ value: "draft", label: "Draft" }` (первой опцией после "All").

2. **Бейдж в колонке статуса.** Найти место, где рендерится бейдж статуса (искать существующий компонент/функцию `getStatusBadge` или inline-классы по `row.status`). Добавить ветку для `"draft"` — например, серый бейдж `Draft`.

3. **Клик по строке.** Найти `onRowClick` / `<tr onClick>` (вероятно ниже 220-й строки или в колонке `name`). Добавить условие:
   ```ts
   if (project.status === "draft") {
     setEditDraftProject(project);  // новый useState
     setIsCreateOpen(true);          // или отдельный isEditDraftOpen
   } else {
     navigate(`/projects/${project.id}`);
   }
   ```
   А в JSX модалки:
   ```tsx
   <CreateProjectModal
     isOpen={isCreateOpen}
     onClose={() => { setIsCreateOpen(false); setEditDraftProject(null); }}
     mode={editDraftProject ? "edit-draft" : "create"}
     draftProject={editDraftProject ?? undefined}
   />
   ```

## Критические файлы
- [app/models/project.py](app/models/project.py) — снять nullable=False с 5 колонок.
- [app/schemas/project.py](app/schemas/project.py) — добавить `SiteProjectDraftCreate`, `SiteProjectUpdate`; разрешить null в `SiteProjectResponse`.
- [app/api/projects.py](app/api/projects.py) — три новых эндпоинта + правка `not_in` фильтра в `create_project`.
- alembic/versions/<new>.py — миграция nullable.
- [frontend/src/api/projects.ts](frontend/src/api/projects.ts) — `saveDraft`, `updateDraft`, `launchDraft` + типы.
- [frontend/src/pages/ProjectsPage.tsx](frontend/src/pages/ProjectsPage.tsx) — пропсы и кнопки модалки, бейдж и клик в списке, расширение `STATUS_OPTIONS`.

## Верификация

1. **Миграция.** `alembic upgrade head` локально на dev-БД; проверить `\d site_projects` — целевые поля nullable.
2. **Юнит-уровень.** `python -m pytest tests/ -k project` — никаких регрессий в существующих тестах создания/листинга/удаления.
3. **End-to-end через UI** (запустить backend `uvicorn app.main:app --reload` и `npm run dev` в `frontend/`):
   - Открыть «Add Project», ввести только `Name`, нажать `Save Draft` → toast `Draft saved`, в списке проектов появилась строка со статусом `Draft`.
   - Кликнуть по строке черновика → попап открывается с предзаполненным `Name`, остальные поля пустые.
   - Дозаполнить blueprint/seed/country/language/target_site, нажать `Save Draft` → toast `Draft saved`, попап закрылся, при следующем открытии черновика — поля сохранены.
   - Нажать `Launch Project` без обязательных полей → toast с ошибкой валидации (frontend).
   - Заполнить все обязательные → `Launch Project` → toast `Project launched`, статус становится `pending`/`generating`, Celery-задача появилась в логах воркера.
   - Создать ещё один черновик с теми же blueprint+seed+target_site → существующий активный (не draft) проект корректно отлавливается duplicate-check’ом при `Launch`, но не при `Save Draft`.
4. **Удаление.** Удалить черновик из списка (force не требуется) — должен пропасть.
5. **Запуск без worker’а.** Если Celery-воркер не запущен, `Launch` должен вернуть 503 от `_ensure_worker_available()` — проверить, что состояние черновика остаётся `draft` (откатить `status` в случае исключения после изменения, если этого нет — добавить try/except).

## Риски / открытые вопросы

- `SiteProjectResponse.site_id: str` сейчас используется в фронтовых типах не только для списка, но и для деталей. Сделав поле `str | None`, нужно убедиться, что страница `/projects/:id` корректно работает или хотя бы не открывается для draft (по плану — клик по draft не ведёт на детальную страницу).
- При `launch` на месте «исходного» `create_project` вся валидация повторяется. Чтобы не дублировать код, можно вынести общий блок (resolve_site, duplicate_check, нормализация serp/keywords/ltm, auto-assign author) в helper и переиспользовать из обоих хендлеров. Это улучшение опционально, не блокирует базовую реализацию.
