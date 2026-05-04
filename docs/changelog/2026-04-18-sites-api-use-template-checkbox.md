# 18 апреля 2026 — Sites API и чекбокс Use site HTML template

**Дата:** 2026-04-18
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Цель:** UI **Create Generative Project** стабильно отражает наличие HTML-шаблона у сайта (**`sites.template_id`**), в т.ч. после частичного деплоя и при устаревшем кэше React Query; пользователь всегда видит опцию **Use site HTML template** после выбора сайта, даже если шаблона нет (тогда чекбокс недоступен и объяснено поведение).

**Backend — `app/api/sites.py` (`_site_out`)**
- В JSON каждого сайта: **`template_id`**, **`template_name`**, **`has_template`** (`bool(s.template_id)`).

**Frontend — `frontend/src/pages/ProjectsPage.tsx` (модалка создания проекта)**
- Запрос списка сайтов: **`refetchOnMount: "always"`** для ключа **`["sites"]`**.
- При непустом **`site_id`**: **`useQuery`** → **`sitesApi.getOne(id)`** (ключ **`["sites", site_id]`**), **`selectedSite`** = деталка или строка из списка.
- **`siteHasTemplate`** = **`selectedSite?.has_template ?? Boolean(selectedSite?.template_id)`**.
- **Показ блока с чекбоксом:** при **`formData.site_id`** (не только при **`siteHasTemplate`**).
- **`onSiteChange`:** **`use_site_template`** = **`has_template ?? Boolean(template_id)`** у выбранного сайта из списка (нет шаблона → **`false`** по умолчанию).
- **`useEffect`:** если **`siteHasTemplate`** ложен, а **`use_site_template`** ещё **`true`** (например, после дозагрузки деталки) — сброс в **`false`**.
- **Чекбокс:** **`disabled={!siteHasTemplate}`**; подсказка при отсутствии шаблона: *«No HTML template assigned to this site…»*; при наличии шаблона — прежний текст про отключение обёртки.

**Тесты**
- **`tests/test_sites_api.py`** — проверки **`has_template`** для сайта с шаблоном и без.

**Docker: когда «на фронте ничего нового»**
- Сервис **`frontend`** собирает **`npm run build`** **внутри образа** (нет volume с исходниками). После правок TS/React: **`docker compose build --no-cache frontend`**, затем **`docker compose up -d --force-recreate frontend`**.
- По умолчанию UI на хосте: **`http://localhost:3001`** (переменная **`FRONTEND_HOST_PORT`** в **`.env`** / compose; не путать с **`8000`** бэкенда или локальным **`npm run dev`**).
- Проверка, что строка попала в сборку:  
  **`docker compose exec frontend sh -c 'grep -l "Use site HTML template" /app/dist/assets/*.js'`**  
  (ожидаются в т.ч. **`ProjectsPage-*.js`**, **`ProjectDetailPage-*.js`**). Чанк **`ProjectsPage`** подгружается при заходе на **`/projects`** — нужен жёсткий refresh (**Cmd+Shift+R**) / инкогнито при закэшированном **`index.html`**.

---
