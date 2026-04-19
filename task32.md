# Plan: Allow skipping Target Site when creating a project ("markup only" mode)

## Context

Пользователь несколько раз просил возможность создавать проект **без выбора Target Site** — нужна просто разметка (content-only), без «обёртки» сайта (head / header / footer). После нескольких итераций фронт всё ещё помечает поле `Target Site *` как обязательное и блокирует submit.

### Почему изменения не «прилипали»

Это **не просто чек на фронте** — требование защищено в трёх местах:

1. **Frontend** — [ProjectsPage.tsx:887-903](frontend/src/pages/ProjectsPage.tsx:887): `<label>Target Site *</label>` + `<select required>`.
2. **Frontend validation** — [ProjectsPage.tsx:769-781](frontend/src/pages/ProjectsPage.tsx:769): `handleSubmit` падает с toast «Please fill in all required fields», если `!formData.site_id`.
3. **Backend schema** — [app/api/projects.py:241](app/api/projects.py:241): `SiteProjectCreate.target_site: str` (non-Optional), аналогично `ProjectPreviewRequest.target_site: str` ([projects.py:268](app/api/projects.py:268)).
4. **DB ограничение** — [app/models/project.py:14](app/models/project.py:14): `SiteProject.site_id = Column(..., nullable=False)`. Каждый проект обязан быть привязан к строке в таблице `sites`.

То есть даже если убрать `required` с `<select>`, бэк всё равно вернёт 422, а БД не даст вставить строку без `site_id`. Прежние попытки, судя по всему, меняли только UI-слой.

### Хорошая новость

В системе уже есть ровно тот флаг, который пользователю нужен по смыслу:
`use_site_template: bool` ([projects.py:248](app/api/projects.py:248), [models/project.py:47](app/models/project.py:47)). Когда он `false`, `template_engine.py:26` и `pipeline.py:914` пропускают обёртку сайта и выдают «голую» разметку. Проблема только в том, что UI всё равно заставляет выбрать сайт.

Плюс `_resolve_site` ([projects.py:159-185](app/api/projects.py:159)) умеет **автосоздавать** Site по имени/домену, если его нет.

## Решение

Ввести явный режим **«Markup only»** в модалке создания проекта. Когда он включён:

- Target Site в UI скрывается и не требуется.
- На бэке `target_site` становится optional; при отсутствии мы переиспользуем (или создаём один раз) зарезервированный placeholder-Site (`__markup_only__`) — это удовлетворит NOT NULL на `site_id`, не трогая схему БД.
- `use_site_template` принудительно ставится в `false` — на выходе будет чистая разметка.
- `country` / `language` берутся напрямую из формы (сейчас они автозаполнялись из выбранного сайта — см. [ProjectsPage.tsx:833-834](frontend/src/pages/ProjectsPage.tsx:833)).

Никаких миграций БД, никаких изменений в `SiteProject` модели, никаких переписываний pipeline — только расширение уже существующих контрактов.

## Изменения по файлам

### Backend — [app/api/projects.py](app/api/projects.py)

1. **[projects.py:241](app/api/projects.py:241)** — `SiteProjectCreate`:
   - `target_site: str` → `target_site: Optional[str] = None`
2. **[projects.py:268](app/api/projects.py:268)** — `ProjectPreviewRequest`:
   - `target_site: str` → `target_site: Optional[str] = None`
3. Добавить константу и helper рядом с `_resolve_site`:
   ```python
   MARKUP_ONLY_SITE_KEY = "__markup_only__"

   def _resolve_site_or_markup_only(db, target_site, country, language, use_site_template):
       if target_site and target_site.strip():
           return _resolve_site(db, target_site, country, language), use_site_template
       site = _resolve_site(db, MARKUP_ONLY_SITE_KEY, country, language)
       return site, False  # markup-only projects всегда без шаблона
   ```
4. **[projects.py:585](app/api/projects.py:585)** (create endpoint) и **[projects.py:941-944](app/api/projects.py:941)** (clone endpoint) — вызывать новый helper вместо прямого `_resolve_site`, и использовать возвращённый `use_site_template` при создании `SiteProject`.
5. **[projects.py:397](app/api/projects.py:397)** (preview endpoint) — если `body.target_site` пустой, возвращать preview без site-template-части (существующая ветка `site_will_create` уже близка).

### Frontend — [frontend/src/pages/ProjectsPage.tsx](frontend/src/pages/ProjectsPage.tsx)

1. В state добавить флаг `markup_only: false` (рядом с `use_site_template` на [ProjectsPage.tsx:553](frontend/src/pages/ProjectsPage.tsx:553)).
2. Над блоком Target Site (перед [ProjectsPage.tsx:886](frontend/src/pages/ProjectsPage.tsx:886)) добавить чекбокс **«Markup only (skip target site — output content without site wrapper)»**.
3. Когда `markup_only === true`:
   - Скрыть блок Target Site (`[ProjectsPage.tsx:886-903]`) и блок выбора шаблона (`[ProjectsPage.tsx:904-925]`), либо рендерить их задизейбленными.
   - Форсить `site_id=""`, `use_site_template=false`.
4. В `handleSubmit` ([ProjectsPage.tsx:769-781](frontend/src/pages/ProjectsPage.tsx:769)) убрать `!formData.site_id` из проверки, когда `markup_only` включён; текст ошибки поправить соответственно.
5. В payload ([ProjectsPage.tsx:809-822](frontend/src/pages/ProjectsPage.tsx:809)) передавать `target_site: markup_only ? undefined : formData.site_id`.
6. Тип `SiteProjectCreatePayload` (см. [frontend/src/api/projects.ts](frontend/src/api/projects.ts) и [frontend/src/types/project.ts](frontend/src/types/project.ts)) — сделать `target_site?: string` (optional). Убедиться, что preview-запрос тоже использует optional.
7. Country/Language: оставить обязательными (они уже есть в форме и в валидации); просто они больше не автозаполняются из сайта в markup-only режиме — пользователь выбирает вручную.

## Критичные файлы

- [app/api/projects.py](app/api/projects.py) — схемы `SiteProjectCreate` / `ProjectPreviewRequest`, функция `_resolve_site`, create/preview/clone endpoints.
- [app/models/project.py](app/models/project.py) — **не трогаем** (`site_id` остаётся NOT NULL).
- [frontend/src/pages/ProjectsPage.tsx](frontend/src/pages/ProjectsPage.tsx) — модалка Create Generative Project.
- [frontend/src/api/projects.ts](frontend/src/api/projects.ts), [frontend/src/types/project.ts](frontend/src/types/project.ts) — TS-типы payload'ов.

## Verification

1. Запустить бэк и фронт (обычный dev-запуск проекта). Открыть http://localhost:3001/projects → Create.
2. **Позитив 1 (markup only):** включить новый чекбокс «Markup only», заполнить Name / выбрать Blueprint / Seed / выбрать Country / Language, submit. Проект должен создаться; в карточке проекта `use_site_template=false`, site привязан к placeholder `__markup_only__`.
3. **Позитив 2 (обычный режим):** без галочки — всё работает как раньше, Target Site обязателен на фронте.
4. **Негатив:** при включённой галочке оставить Country/Language пустыми — форма должна показать старую ошибку валидации (они всё ещё required).
5. Проверить, что сгенерированные страницы в markup-only проекте не содержат `<html>/<head>/<header>/<footer>` обвязки (только контент-разметка) — это уже покрыто веткой `use_site_template=false` в `template_engine.py:26` / `pipeline.py:914`.
6. Preview-кнопка в модалке должна работать и без выбранного сайта, когда markup-only включён.
7. Clone существующего проекта без указания `target_site` должен по-прежнему наследовать site оригинала (эта ветка в [projects.py:944](app/api/projects.py:944) не меняется — `body.target_site is None` → использует `src.site_id`).
