# 28 марта 2026 — парсер MULTIMEDIA для image pipeline (`image_utils.py`)

**Дата:** 2026-03-28
**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md

**Проблема:** outline на языке статьи даёт ключи вроде `МУЛЬТИМЕДИА`, `MULTIMÉDIA`, `medien` и т.д.; раньше искалось только английское `MULTIMEDIA`.

**Реализовано**
- Набор **`MULTIMEDIA_KEY_VARIANTS`** и **`_is_multimedia_key()`** — мультиязычные и альтернативные ключи (`image_description`, `visual`, `изображение`, …), префиксы с номером (`multimedia_5`, `мультимедиа_4`, …).
- Значение multimedia-ключа: **dict** (как раньше), **строка** (>10 символов) → разбор через **`_parse_multimedia_from_text`**, **список** dict/строк → несколько блоков.
- Сканирование **длинных строковых** полей dict (**> 30** символов) на встройки: скобки `[MULTIMEDIA: …]`, жирный markdown, тире после тега, типовые `[Image: …]` / `[Инфографика: …]` — функции **`_extract_multimedia_from_text_content`**, regex по тегам EN/RU/FR/DE/ES/IT/PL.
- **`phase_image_prompt_gen`**: если **`extract_multimedia_blocks(outline_json)`** вернул пусто, а сырой результат final structure **> 100** символов — повторный поиск через **`_extract_multimedia_from_text_content(outline_raw, "outline_raw")`** + лог `info`; если блоков нет — лог **`[DEBUG]`** с первыми 1500 символами outline + прежние предупреждения.
- Тесты: **`tests/test_image_utils.py`** (в т.ч. русский/французский ключ и текст, строка, список, смешанные языки).

---
