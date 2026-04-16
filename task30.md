# ТЗ: Рефакторинг Legal Page Templates

**Версия:** 1.0  
**Дата:** 16 апреля 2026  
**Контекст:** Система массовой SEO-генерации текстов. Вкладка Legal Page Templates требует рефакторинга — убрать дубли стран, упростить формат контента, добавить выбор шаблонов в форме создания проекта. Пайплайн должен брать текст-образец из шаблона и адаптировать его через LLM под страну/домен/язык проекта.

---

## Часть 1 — Рефакторинг модели LegalPageTemplate

### 1.1. Убрать привязку к стране из модели

**Текущее состояние:**
- Модель `LegalPageTemplate` (`app/models/template.py`) содержит поле `country` (String(10)) с UniqueConstraint на пару `(country, page_type)`.
- В списке стран фронтенда (`LegalPagesPage.tsx`) — дубликаты: `FR` и `FRANCE`, `DE` и `GERMANY` и т.д., потому что список собирается из `authors.country` + хардкод.

**Что сделать:**

**Модель (`app/models/template.py`):**
- Удалить поле `country` из `LegalPageTemplate`.
- Удалить `UniqueConstraint("country", "page_type", name="uq_legal_page_templates_country_page_type")`.
- Добавить поле `name` — `Column(String(200), nullable=False)`. Это человекочитаемое имя шаблона, например: "Casino Privacy Policy", "Generic Terms & Conditions", "Responsible Gambling (UK style)".
- Добавить `UniqueConstraint("name", "page_type", name="uq_legal_tpl_name_page_type")` — чтобы не было двух шаблонов с одним именем и типом.
- Поле `html_content` переименовать в `content` (Text, nullable=False) — т.к. теперь принимает и plain text.
- Добавить поле `content_format` — `Column(String(10), nullable=False, default="text")`. Допустимые значения: `"text"`, `"html"`. Информационное — для подсветки в UI, пайплайн использует as-is.

Итоговая модель:
```python
class LegalPageTemplate(Base):
    __tablename__ = "legal_page_templates"
    __table_args__ = (
        UniqueConstraint("name", "page_type", name="uq_legal_tpl_name_page_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)          # NEW
    page_type = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)               # RENAMED from html_content
    content_format = Column(String(10), nullable=False, default="text")  # NEW: "text" | "html"
    variables = Column(JSONB, nullable=False, default=dict)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 1.2. Alembic-миграция

Файл: `alembic/versions/XXX_refactor_legal_page_templates.py`

Шаги миграции:
1. Добавить колонку `name` (String(200), nullable=True временно).
2. Заполнить `name` из существующих записей: `UPDATE legal_page_templates SET name = country || ' — ' || page_type` (чтобы не потерять данные).
3. Сделать `name` NOT NULL.
4. Добавить колонку `content_format` (String(10), default="html", NOT NULL) — существующие записи считаем HTML.
5. Переименовать колонку `html_content` → `content`.
6. Удалить constraint `uq_legal_page_templates_country_page_type`.
7. Удалить колонку `country`.
8. Создать constraint `uq_legal_tpl_name_page_type`.

---

## Часть 2 — Рефакторинг API (backend)

### 2.1. Эндпоинты Legal Pages (`app/api/legal_pages.py`)

**Pydantic-схемы — обновить:**

```python
class LegalPageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    page_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)  # was html_content
    content_format: str = Field(default="text", pattern="^(text|html)$")
    variables: dict = Field(default_factory=dict)
    notes: Optional[str] = None
    is_active: bool = True


class LegalPageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    page_type: Optional[str] = Field(None, min_length=1, max_length=50)
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    content: Optional[str] = None  # was html_content
    content_format: Optional[str] = Field(None, pattern="^(text|html)$")
    variables: Optional[dict] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
```

**Эндпоинт `GET /` (list):**
- Убрать query-параметр `country`.
- Добавить опциональный `page_type: Optional[str]` для фильтрации.
- В ответ добавить `name` и `content_format`.

**Эндпоинт `GET /{legal_id}`:**
- Возвращать `content` вместо `html_content`, плюс `name`, `content_format`.

**Эндпоинт `POST /`:**
- Проверять дубликат по `(name, page_type)` вместо `(country, page_type)`.

**Эндпоинт `PUT /{legal_id}`:**
- Аналогично, дубликат по `(name, page_type)`.

**Добавить новый эндпоинт `GET /by-page-type/{page_type}`:**
- Возвращает все активные шаблоны для данного `page_type`. Нужен для дропдаунов в форме проекта.
- Ответ: `[{id, name, page_type, title, content_format}]`.

### 2.2. Новый эндпоинт: Legal templates для Blueprint

**`GET /api/legal-pages/for-blueprint/{blueprint_id}`**

Логика:
1. Загрузить все `BlueprintPage` для blueprint_id.
2. Отфильтровать те, где `page_type in LEGAL_PAGE_TYPES` (из `app/models/template.py`).
3. Для каждого найденного legal page_type вернуть список доступных `LegalPageTemplate` (active).

Ответ:
```json
{
  "legal_page_types": [
    {
      "page_type": "privacy_policy",
      "page_title": "Privacy Policy",
      "templates": [
        {"id": "uuid-1", "name": "Casino Privacy Policy", "title": "Privacy Policy"},
        {"id": "uuid-2", "name": "Generic GDPR Privacy", "title": "Privacy Policy (GDPR)"}
      ]
    },
    {
      "page_type": "responsible_gambling",
      "page_title": "Responsible Gambling",
      "templates": [
        {"id": "uuid-3", "name": "UK Gambling Commission Style", "title": "Responsible Gambling"}
      ]
    }
  ]
}
```

Если в Blueprint нет legal-страниц — вернуть пустой массив `{"legal_page_types": []}`.

---

## Часть 3 — Привязка шаблонов к проекту

### 3.1. Модель SiteProject (`app/models/project.py`)

Добавить поле:
```python
legal_template_map = Column(
    JSONB,
    nullable=True,
    default=dict,
    comment="Mapping page_type -> legal_page_template_id. Example: {'privacy_policy': 'uuid-1', 'responsible_gambling': 'uuid-3'}"
)
```

### 3.2. Alembic-миграция

Добавить колонку `legal_template_map` (JSONB, nullable=True, default='{}') в `site_projects`.

### 3.3. API Projects (`app/api/projects.py`)

**`SiteProjectCreate`** — добавить:
```python
legal_template_map: Optional[Dict[str, str]] = None  # {page_type: template_id}
```

**`SiteProjectCloneBody`** — добавить:
```python
legal_template_map: Optional[Dict[str, str]] = None
```

**Создание проекта** (`POST /projects`):
- Если `legal_template_map` передан — валидировать: каждый ключ должен быть в `LEGAL_PAGE_TYPES`, каждое значение — существующий активный `LegalPageTemplate.id` с matching `page_type`.
- Сохранить в `project.legal_template_map`.

**Ответ `GET /projects/{id}`:**
- Добавить `legal_template_map` в ответ.

**Clone:**
- Копировать `legal_template_map` из исходного проекта, если не переопределён в body.

---

## Часть 4 — Изменение пайплайна

### 4.1. `app/services/legal_reference.py`

**Новая логика `inject_legal_template_vars`:**

```python
def inject_legal_template_vars(ctx: Any) -> None:
    """
    Fill legal_reference_html and legal_variables.
    
    Приоритет поиска шаблона:
    1. project.legal_template_map[page_type] — явный выбор пользователя
    2. Если нет — пустой reference (LLM генерирует без образца)
    """
    ctx.template_vars["legal_reference_html"] = ""
    ctx.template_vars["legal_variables"] = "{}"

    if ctx.use_serp:
        return
    if ctx.task.page_type not in LEGAL_PAGE_TYPES:
        return

    site = ctx.db.query(Site).filter(Site.id == ctx.task.target_site_id).first()
    if not site:
        return

    # --- Новая логика: ищем шаблон через project.legal_template_map ---
    template_id = None
    
    # Попробовать взять из проекта
    if ctx.task.project_id:
        from app.models.project import SiteProject
        project = ctx.db.query(SiteProject).filter(SiteProject.id == ctx.task.project_id).first()
        if project and isinstance(project.legal_template_map, dict):
            template_id = project.legal_template_map.get(ctx.task.page_type)
    
    lp = None
    if template_id:
        lp = (
            ctx.db.query(LegalPageTemplate)
            .filter(
                LegalPageTemplate.id == template_id,
                LegalPageTemplate.is_active == True,
            )
            .first()
        )
    
    if not lp:
        # Нет шаблона — LLM генерирует без reference
        return

    legal_info = site.legal_info if isinstance(site.legal_info, dict) else {}
    content = substitute_legal_html(lp.content or "", legal_info)
    ctx.template_vars["legal_reference_html"] = content

    merged: dict[str, Any] = {}
    if isinstance(lp.variables, dict):
        merged.update(lp.variables)
    merged.update(legal_info)
    ctx.template_vars["legal_variables"] = json.dumps(merged, ensure_ascii=False)
```

**Важно:** Функция `substitute_legal_html` — переименовать внутри параметр `html` → `content` (косметика, но consistency).

### 4.2. Промпт `primary_generation_legal` (seeds / DB)

Текущий промпт ссылается на `{{legal_reference_html}}`. Переименовывать переменную не нужно — она остаётся `legal_reference_html` в template_vars, просто теперь может содержать plain text. Но стоит обновить формулировку в промпте:

**Было:**
```
REFERENCE LEGAL TEMPLATE (use as structural and stylistic guide):
{{legal_reference_html}}
```

**Стало:**
```
REFERENCE LEGAL TEMPLATE (use as structural and stylistic guide — may be HTML or plain text):
{{legal_reference_html}}

If the reference is empty, generate the page from scratch based on best practices for the given page_type and country.
```

---

## Часть 5 — Фронтенд

### 5.1. Страница Legal Page Templates (`LegalPagesPage.tsx`)

**Убрать полностью:**
- `useMemo` с `countries` (сборка из авторов + хардкод).
- Фильтр по country в toolbar.
- Колонку `country` из таблицы.
- Поле `Country *` из модальной формы.

**Добавить:**
- Колонку `Name` в таблицу (первой).
- Фильтр по `page_type` вместо country.
- Поле `Name *` в форму создания/редактирования (text input).
- Поле `Content Format` в форму — тумблер или radio: "Plain Text" / "HTML". Влияет на подсветку Monaco (language="html" vs language="plaintext").
- Изменить default value `content` с `<!DOCTYPE html>\n<html><body></body></html>` на пустую строку `""`.
- Лейбл поля контента: `"Content *"` вместо `"HTML Content *"`. Подпись: `"Reference text for LLM. Can be plain text or HTML."`.

**Типы (`frontend/src/types/template.ts`):**

Обновить `LegalPageTemplateRow`:
```typescript
export interface LegalPageTemplateRow {
  id: string;
  name: string;          // NEW
  page_type: string;
  title: string;
  content_format: string; // NEW: "text" | "html"
  is_active: boolean;
}
```

**API клиент (`frontend/src/api/legalPages.ts`):**
- Обновить типы запросов/ответов: `html_content` → `content`, добавить `name`, `content_format`.
- Убрать параметр `country` из `getAll()`.
- Добавить метод `getForBlueprint(blueprintId: string)` — вызывает `GET /api/legal-pages/for-blueprint/{blueprintId}`.

### 5.2. Форма создания проекта (`ProjectsPage.tsx`)

**Когда показывать секцию Legal Templates:**
- Пользователь выбирает Blueprint → фронтенд вызывает `GET /api/legal-pages/for-blueprint/{blueprint_id}`.
- Если ответ содержит `legal_page_types.length > 0` — показать секцию.
- Если нет legal страниц в Blueprint — секцию не показывать.

**UI секции:**
- Расположение: после поля `Author` (или после SERP Config), перед кнопкой Create.
- Заголовок: **"Legal Page Templates (optional)"**
- Подпись: *"Select reference templates for legal pages in this blueprint. LLM will adapt them to your site's country, language, and domain."*
- Для каждого `page_type` из ответа — один дропдаун:
  - Лейбл: `PAGE_TYPE_LABELS[page_type]` (например "Privacy Policy", "Responsible Gambling")
  - Опции: `"— None (generate from scratch) —"` + список шаблонов `[{id, name}]`
  - Default: `"— None —"`

**Стейт формы:**
```typescript
// Добавить в formData:
legal_template_map: Record<string, string>  // {page_type: template_id}
```

**При submit:**
- Собрать `legal_template_map` только из тех дропдаунов, где выбран конкретный шаблон (не "None").
- Передать в `SiteProjectCreatePayload.legal_template_map`.

### 5.3. Страница деталей проекта

В секции с информацией о проекте показать выбранные legal templates:
- Если `legal_template_map` не пустой — отобразить как read-only список: `"Privacy Policy → Casino Privacy Policy"`, `"Responsible Gambling → UK Gambling Commission Style"`.
- Если пустой — ничего не показывать или `"Legal templates: not configured"`.

---

## Часть 6 — Унификация стран по всей системе (отдельная задача)

Это **не блокирует** основной рефакторинг (мы убрали country из LegalPageTemplate), но полезно сделать параллельно.

### 6.1. Централизованный справочник стран

Файл `frontend/src/constants/countries.ts`:
```typescript
export const COUNTRIES: { code: string; label: string }[] = [
  { code: "AT", label: "Austria" },
  { code: "AU", label: "Australia" },
  { code: "BE", label: "Belgium" },
  { code: "BR", label: "Brazil" },
  { code: "CA", label: "Canada" },
  { code: "CH", label: "Switzerland" },
  { code: "DE", label: "Germany" },
  { code: "DK", label: "Denmark" },
  { code: "ES", label: "Spain" },
  { code: "FR", label: "France" },
  { code: "GB", label: "Great Britain" },
  { code: "IT", label: "Italy" },
  { code: "NL", label: "Netherlands" },
  { code: "PL", label: "Poland" },
  { code: "US", label: "United States" },
  // расширять по мере надобности
];

export const COUNTRY_CODES = COUNTRIES.map(c => c.code);
export const countryLabel = (code: string) =>
  COUNTRIES.find(c => c.code === code)?.label ?? code;
```

### 6.2. Применить справочник

Заменить во всех местах, где сейчас список стран собирается из авторов:
- `LegalPagesPage.tsx` — УДАЛЕНО (country убран из модели).
- `TasksPage.tsx` (CreateTaskModal) — дропдаун `Country *` → использовать `COUNTRIES` из constants, показывать `${code} — ${label}`. Параллельно оставить авторские страны для обратной совместимости.
- `ProjectsPage.tsx` (CreateGenerativeProject) — аналогично.
- `SiteDetailPage.tsx` — поле `Country` сайта → аналогично.

### 6.3. Миграция данных авторов

SQL-миграция для нормализации `authors.country`:
```sql
UPDATE authors SET country = 'FR' WHERE UPPER(country) IN ('FRANCE', 'FRENCH');
UPDATE authors SET country = 'DE' WHERE UPPER(country) IN ('GERMANY', 'GERMAN', 'DEUTSCHLAND');
UPDATE authors SET country = 'GB' WHERE UPPER(country) IN ('GREAT BRITAIN', 'UK', 'UNITED KINGDOM', 'ENGLAND');
UPDATE authors SET country = 'AU' WHERE UPPER(country) IN ('AUSTRALIA', 'AUSTRALIAN');
UPDATE authors SET country = 'BE' WHERE UPPER(country) IN ('BELGIUM', 'BELGIAN');
UPDATE authors SET country = 'CA' WHERE UPPER(country) IN ('CANADA', 'CANADIAN');
UPDATE authors SET country = 'DK' WHERE UPPER(country) IN ('DENMARK', 'DANISH');
UPDATE authors SET country = 'PL' WHERE UPPER(country) IN ('POLAND', 'POLISH');
UPDATE authors SET country = UPPER(TRIM(country)) WHERE LENGTH(country) = 2;
```

Аналогично для `sites.country`.

### 6.4. Бэкенд-валидация

В `app/api/sites.py` (SiteCreate, SiteUpdate) и `app/api/projects.py` (SiteProjectCreate) — добавить валидацию `country`: только 2-символьный uppercase ISO-код. Можно через Pydantic validator:
```python
@field_validator("country")
def validate_country(cls, v):
    v = v.strip().upper()
    if len(v) != 2 or not v.isalpha():
        raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
    return v
```

---

## Порядок выполнения

| #   | Задача                                                                                            | Зависимости | Оценка   |
| --- | ------------------------------------------------------------------------------------------------- | ----------- | -------- |
| 1   | Alembic-миграция: `legal_page_templates` (убрать country, добавить name, content, content_format) | —           | 30 мин   |
| 2   | Alembic-миграция: `site_projects` (добавить legal_template_map)                                   | —           | 15 мин   |
| 3   | Backend: обновить модель `LegalPageTemplate`                                                      | #1          | 15 мин   |
| 4   | Backend: обновить `app/api/legal_pages.py` (схемы, эндпоинты, новый for-blueprint)                | #3          | 1 час    |
| 5   | Backend: обновить `app/api/projects.py` (legal_template_map в create/clone/response)              | #2          | 45 мин   |
| 6   | Backend: обновить `app/services/legal_reference.py` (новая логика поиска шаблона)                 | #3, #2      | 30 мин   |
| 7   | Backend: обновить промпт `primary_generation_legal` в seed и/или DB                               | #6          | 15 мин   |
| 8   | Frontend: обновить типы, API-клиент `legalPages.ts`                                               | #4          | 30 мин   |
| 9   | Frontend: рефакторинг `LegalPagesPage.tsx` (убрать country, добавить name, content format)        | #8          | 1.5 часа |
| 10  | Frontend: добавить секцию Legal Templates в `ProjectsPage.tsx` (CreateGenerativeProject)          | #4, #8      | 2 часа   |
| 11  | Frontend: показать legal_template_map на странице деталей проекта                                 | #5          | 30 мин   |
| 12  | (Параллельно) Унификация стран: constants, миграция авторов, валидация                            | —           | 2 часа   |

**Общая оценка:** ~9–10 часов.

---

## Что НЕ меняется (для ясности)

- `LEGAL_PAGE_TYPES` — остаётся как есть (`privacy_policy`, `terms_and_conditions`, `cookie_policy`, `responsible_gambling`, `about_us`).
- Pipeline presets (`legal` → `[STEP_PRIMARY_GEN_LEGAL, STEP_META_GEN]`) — не меняется.
- Blueprint pages с `page_type` в legal — не меняются, остаются как сейчас.
- Поле `Site.legal_info` (JSON с company_name, contact_email и т.д.) — не меняется, по-прежнему подставляется в шаблон.
- Template переменные `{{legal_reference_html}}` и `{{legal_variables}}` — имена не меняются.
