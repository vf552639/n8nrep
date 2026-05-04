# 11 апреля 2026 — JSON-парсер, `meta_generation`, Top P в Model Settings (UI)

**Дата:** 2026-04-11
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Контекст:** доработки по task25 — корректное извлечение title/description из ответа **`meta_generation`**; универсальный парсер JSON без хардкода ключей **`ai_structure_analysis`**; визуальная согласованность Top P при выключенном тоггле.

**`app/services/json_parser.py` — `clean_and_parse_json(text, unwrap_keys=None)`**
- Универсальный парсинг: снятие markdown-ограждений, при ошибке **`json.loads`** — извлечение первого JSON-объекта через **`JSONDecoder().raw_decode`**, затем запасной regex; устойчивость к тексту до/после JSON и к «хвосту» после валидного объекта.
- Размотка вложенного dict **только** при явном **`unwrap_keys`** (для **`phase_ai_structure`** передаётся **`{"intent", "Taxonomy", "Attention", "structura"}`**). Остальные вызовы (в т.ч. **`meta_generation`**, fact-check) получают внешний объект как есть — без ложного «переезда» в первый вложенный dict.

**`app/services/meta_parser.py`**
- **`extract_meta_from_parsed(meta_data)`** — единое извлечение **`title`**, **`description`**, **`h1`** из ответа **`meta_generation`**: списки под ключами **`results`** / **`variants`** (без учёта регистра), затем любой непустой **`list[dict]`**; плоские поля на верхнем уровне; вложенные dict (обёртки вроде **`response`**). Ключи полей ищутся **без учёта регистра** (**`title`/`meta_title`**, **`description`/`meta_description`**, **`h1`/`heading`/`headline`**).
- **`meta_variant_list(meta_data)`** — полный список вариантов для DOCX (тот же приоритет **`results`** / **`variants`**, иначе первый **`list[dict]`**).
- Алиас **`_extract_meta_from_parsed`** = **`extract_meta_from_parsed`**.

**`app/services/pipeline.py`**
- **`phase_meta_generation`:** после **`call_agent`** — debug-лог **`meta_generation raw (first 500): …`** (шаг **`meta_generation`**).
- **Сборка статьи:** после **`clean_and_parse_json`** — debug-лог **`meta_data keys: …`**; **`extract_meta_from_parsed(meta_data)`** → **`title`**, **`description`**, debug-лог **`meta extracted: title=…, desc=…, h1=…`**; при пустом title — fallback на keyword и предупреждение в логе. Полный JSON по-прежнему в **`meta_data`** у статьи.
- Если для **`task_id`** уже есть **`GeneratedArticle`** — **обновление** строки (title, description, **`meta_data`**, HTML, **`full_page_html`**, **`word_count`**, fact-check поля, **`needs_review`**), а не только создание новой.
- **`meta_json_str`** не-строка (edge case) — приводится к JSON-строке перед парсингом.

**`app/services/docx_builder.py`**
- **`_get_all_meta_from_task`:** парсинг шага **`meta_generation`** через **`clean_and_parse_json`**; мета для таблицы/DOCX — **`extract_meta_from_parsed`**; **`all_variants`** — **`meta_variant_list`** (поддержка **`variants`**, произвольных списков вариантов).

**Frontend — `frontend/src/pages/PromptsPage.tsx` (Top P)**
- При выключенном тоггле **`top_p`**: отображение **`0`**, при снятии тоггла — **`top_p: 0`** в **`editState`**; fallbacks **`?? 0`** для поля, слайдера, **`isPromptDirty`**, **`PromptTestPanel`**, сохранения (**`PUT /api/prompts/{id}`** с **`top_p: 0`** при **`top_p_enabled: false`**). Логика **`prompt_llm_kwargs`** / OpenRouter без изменений — при **`top_p_enabled=false`** ключ **`top_p`** в запрос не попадает.

**Тесты:** **`tests/test_json_parser.py`** (перенесены сценарии с прежнего **`tests/test_pipeline.py`** + новые кейсы meta / **`unwrap_keys`**); **`tests/test_meta_parser.py`** — форматы **`results`** / **`VARIANTS`**, flat, вложенные обёртки, приоритет списков.

---
