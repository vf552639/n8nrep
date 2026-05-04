# 28 марта 2026 — статьи: `meta_data`, контроль слов по шагам

**Дата:** 2026-03-28
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Актуализация (2.04.2026):** если JSON от `meta_generation` имеет вид **`{"results": [...]}`**, поля **`title`/`description` статьи** заполняются из **первого варианта** (ключи `Title`/`Description` или `title`/`description`); см. раздел **«2 апреля 2026»** выше.

**Backend**
- Модель **`GeneratedArticle`**: колонка **`meta_data`** (JSONB) — полный распарсенный ответ агента `meta_generation`; заполняется при сборке статьи в конце `run_pipeline`. Миграция Alembic: `d1e2f3a4b5c6_add_meta_data_to_generated_articles`.
- **`GET /api/articles/{id}`** возвращает **`meta_data`**.
- **`app/services/word_counter.py`**: **`count_content_words()`** — слова видимого текста (HTML через BeautifulSoup, без тегов).
- **`save_step_result`** принимает опционально **`input_word_count`**, **`output_word_count`**, **`word_count_warning`**, **`word_loss_percentage`**.
- Подсчёт слов и запись в шаг: **`primary_generation`** (output), **`improver`**, **`final_editing`**, **`html_structure`** (при потере **> 7%** слов контента — `add_log` warn + флаги в step_data), **`image_inject`**.
- **`word_count` статьи** считается через **`count_content_words`** по финальному HTML контента.

**Frontend**
- Тип **`Article`**: поле **`meta_data`**.
- **`ArticleDetailPage`**, вкладка **metadata**: если **`meta_data`** непустой объект — все ключи JSON отдельными блоками (для `title` / `description` сохранены подсказки по длине); иначе прежний вид.
- **`LlmStepView`**: строка **`📊 Words: …`** при наличии счётчиков; красный алерт при **`word_count_warning`**; цвет строки по диапазонам потери (зелёный / янтарный / красный).

---
