# 21 апреля 2026 — task41: пользовательские URL конкурентов для проекта

**Дата:** 2026-04-21
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** для страниц проекта конкуренты по умолчанию берутся только из SERP (DataForSEO / SerpAPI). Нужно вручную задать дополнительные URL на **`SiteProject`**, смержить их с органикой SERP, убрать дубли **по домену**, затем передать объединённый список в существующий **`phase_scraping`** (**`scrape_urls`**).

**База данных и модель**
- Таблица **`site_projects`**: колонка **`competitor_urls`** (**JSONB**, **`NOT NULL`**, default **`[]`**).
- Миграция **`v0a1b2c3d4e5_add_competitor_urls_to_site_projects`** (`down_revision`: **`u8v9w0x1y2zc`**).
- Модель **`app/models/project.py`** — поле **`SiteProject.competitor_urls`**.

**Утилиты — `app/services/url_utils.py`**
- **`normalize_url(raw)`** — trim, при отсутствии схемы **`https://`**, отбрасывание при пустом **`netloc`**.
- **`domain_of(url)`** — хост в lower case, без префикса **`www.`**.
- **`merge_urls_dedup_by_domain(primary, extra)`** — порядок: сначала уникальные по домену из **`primary`**, затем из **`extra`**; второй элемент кортежа — список user-URL, отброшенных как дубль домена относительно уже встреченных.

**Схемы — `app/schemas/project.py`**
- **`SiteProjectCreate.competitor_urls`**: опционально, до **50** строк после нормализации; невалидные URL отбрасываются.
- **`SiteProjectCloneBody.competitor_urls`**: опционально; при клоне без поля в новый проект пишется **`[]`** (список с исходного проекта не копируется).
- **`SiteProjectResponse`**: поле **`competitor_urls`**.

**API — `app/api/projects.py`**
- **`POST /api/projects`**: **`competitor_urls=list(project_in.competitor_urls or [])`** при создании **`SiteProject`**.
- **`POST /api/projects/{id}/clone`**: **`competitor_urls`** из тела, если передано; иначе **`[]`**.
- **`GET /api/projects`**, **`GET /api/projects/{id}`**: в JSON добавлено **`competitor_urls`**.

**Pipeline — `app/services/pipeline.py`, `phase_serp`**
- После успешного **`fetch_serp_data`**, до **`ctx.task.serp_data = serp_data`**: если у задачи есть **`project_id`** и у проекта непустой **`competitor_urls`**, нормализованные user-URL мержатся с **`serp_data["urls"]`** через **`merge_urls_dedup_by_domain`**.
- В **`serp_data`** дополнительно: **`user_competitor_urls`**, **`user_competitor_duplicates`**; лог шага SERP с количеством и дублями.
- В **`serp_summary`** (результат шага в **`step_results`**): **`user_competitor_urls_count`**, **`user_competitor_duplicates`**.

**Frontend**
- **`ProjectsPage.tsx`** (модалка **Create Generative Project**): textarea **Competitor URLs**, парсинг **`parseUrls`** (строка / запятая, max **50**), поле **`competitor_urls`** в payload.
- **`ProjectDetailPage.tsx`**: read-only список сохранённых URL.
- Типы и API: **`SiteProjectCreatePayload`**, **`Project`**, **`ProjectClonePayload`** — **`competitor_urls?`**.

**Тесты**
- **`tests/unit/test_url_utils.py`** — кейсы merge/normalize.
- **`tests/services/test_pipeline_smoke.py`** — **`test_phase_serp_merges_project_competitor_urls`** (**`@pytest.mark.integration`**).
- **`tests/api/test_projects_api.py`** — **`test_create_project_with_competitor_urls`**.
- **`tests/factories.py`** — у **`ProjectFactory`** задано **`competitor_urls=[]`**.

---
