# 30 марта 2026 — Projects: `POST` body, `GET` progress, Axios toast, Error Boundary

**Дата:** 2026-03-30
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Backend (`app/api/projects.py`):**
- **`GET /api/projects`** — в каждом элементе списка поле **`progress`**: 0–100, доля задач проекта со статусом **`completed`**; если задач ещё нет — **0**. Подсчёт одним запросом по **`Task.project_id`** (группировка в Python), без N+1.

**Frontend — создание проекта (`ProjectsPage.tsx`, `frontend/src/api/projects.ts`):**
- Тело **`POST /api/projects`** соответствует **`SiteProjectCreate`**: поле **`target_site`** (UUID выбранного сайта или домен/имя для резолва на бэкенде). Форма UI хранит выбор в **`site_id`**; при сабмите отправляется **`target_site: formData.site_id`**, без поля **`site_id`** (раньше уходило **`site_id`** → **422**). Тип **`SiteProjectCreatePayload`**; **`author_id`** — число или поле не передаётся.
- **`projectsApi.create`** вызывается с **`skipErrorToast: true`** в конфиге Axios, чтобы response interceptor не показывал второй toast; ошибка обрабатывается в **`onError`** мутации через **`formatApiErrorDetail`**.

**Axios (`frontend/src/api/client.ts`, `frontend/src/lib/apiErrorMessage.ts`):**
- В **`toast.error`** попадает только **строка**. Для **`response.data.detail`** используется **`formatApiErrorDetail`**: строка как есть; массив ошибок валидации FastAPI — склейка полей **`msg`**; иначе **`JSON.stringify`**. Это устраняет **React error #31** (объект/массив как React child), в т.ч. при глобальном interceptor.
- Расширение типов: **`frontend/src/types/axios-augment.d.ts`** — флаг **`skipErrorToast`** в **`AxiosRequestConfig`**.

**Error Boundary (`frontend/src/App.tsx`, `frontend/src/components/common/RouteErrorBoundary.tsx`):**
- Маршруты обёрнуты в **`RouteErrorBoundary`** — ошибка рендера в дочернем экране не обнуляет всё приложение (белый экран).
