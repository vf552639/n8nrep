# ТЗ: Расширение парсера MULTIMEDIA — мультиязычность + текстовый парсинг

**Дата:** 28.03.2026  
**Исполнитель:** antigravity  
**Приоритет:** Критический — без этого картинки не генерируются

---

## Суть проблемы

LLM генерирует outline **на языке статьи**. Если статья на французском — ключи и теги будут `MULTIMÉDIA`, на русском — `МУЛЬТИМЕДИА`, на немецком — `MEDIEN` и т.д. Текущий парсер ищет **только английское** `MULTIMEDIA`.

Кроме того, LLM может вписать мультимедиа как:
- JSON-ключ со строкой-значением (не dict)
- Текст внутри поля `Content` / `content` / `structura`
- Альтернативный ключ (`image_description`, `visual`, `illustration`)

---

## Задача 1: Мультиязычные ключи MULTIMEDIA

**Файл:** `app/services/image_utils.py`

Сейчас:
```python
mm_keys = [k for k in obj.keys()
    if isinstance(k, str)
    and (k.upper() == "MULTIMEDIA" or k.upper().startswith("MULTIMEDIA_"))]
```

**Заменить на проверку по расширенному набору:**

```python
# Все варианты написания MULTIMEDIA на разных языках
MULTIMEDIA_KEY_VARIANTS = {
    # English
    "multimedia", "multimedia_1", "multimedia_2", "multimedia_3", "multimedia_4",
    # Russian
    "мультимедиа", "мультимедиа_1", "мультимедиа_2", "мультимедиа_3",
    "медиа", "медиа_1", "медиа_2",
    "изображение", "изображение_1", "изображение_2",
    "картинка", "картинка_1", "картинка_2",
    # French  
    "multimédia", "multimédia_1", "multimédia_2", "multimédia_3",
    "média", "média_1", "média_2",
    "médias", "médias_1",
    # German
    "medien", "medien_1", "medien_2",
    "multimedia_element", "multimedia_element_1",
    "bild", "bild_1", "bild_2",
    # Spanish
    "imagen", "imagen_1", "imagen_2",
    "medio", "medio_1", "medio_2",
    # Italian
    "immagine", "immagine_1", "immagine_2",
    # Polish
    "obraz", "obraz_1", "obraz_2",
    "grafika", "grafika_1", "grafika_2",
    # Portuguese
    "mídia", "mídia_1", "mídia_2",
    "imagem", "imagem_1", "imagem_2",
    # Generic / alternative English keys
    "image", "image_1", "image_2",
    "visual", "visual_1", "visual_2",
    "illustration", "illustration_1", "illustration_2",
    "media", "media_1", "media_2",
    "figure", "figure_1", "figure_2",
    "infographic", "infographic_1", "infographic_2",
    "image_description", "visual_element",
}


def _is_multimedia_key(key: str) -> bool:
    """Check if a JSON key is a multimedia-related key in any supported language."""
    if not isinstance(key, str):
        return False
    k = key.strip().lower()
    
    # Exact match
    if k in MULTIMEDIA_KEY_VARIANTS:
        return True
    
    # Prefix match with underscore + number (e.g. multimedia_5, мультимедиа_4)
    for base in ("multimedia", "мультимедиа", "multimédia", "medien", "média"):
        if k.startswith(base + "_"):
            return True
    
    return False
```

Затем заменить текущее определение `mm_keys`:

```python
# БЫЛО:
mm_keys = [k for k in obj.keys()
    if isinstance(k, str)
    and (k.upper() == "MULTIMEDIA" or k.upper().startswith("MULTIMEDIA_"))]

# СТАЛО:
mm_keys = [k for k in obj.keys() if _is_multimedia_key(k)]
```

---

## Задача 2: Поддержка строкового значения MULTIMEDIA (не только dict)

**Файл:** `app/services/image_utils.py`

Сейчас обработчик ожидает только dict:

```python
for mm_key in mm_keys:
    counter += 1
    blocks.append({
        "id": f"img_{counter}",
        "section": parent_key,
        "section_content": str(obj.get("Content", "") or obj.get("content", ""))[:300],
        "multimedia": _ensure_default_multimedia_type(obj[mm_key]),
    })
```

**Заменить на:**

```python
for mm_key in mm_keys:
    mm_val = obj[mm_key]
    
    if isinstance(mm_val, dict):
        # Existing logic — MULTIMEDIA is a proper dict
        counter += 1
        blocks.append({
            "id": f"img_{counter}",
            "section": parent_key,
            "section_content": str(obj.get("Content", "") or obj.get("content", ""))[:300],
            "multimedia": _ensure_default_multimedia_type(mm_val),
        })
    elif isinstance(mm_val, str) and len(mm_val.strip()) > 10:
        # NEW: MULTIMEDIA key exists but value is a text string
        counter += 1
        parsed_mm = _parse_multimedia_from_text(mm_val)
        blocks.append({
            "id": f"img_{counter}",
            "section": parent_key,
            "section_content": str(obj.get("Content", "") or obj.get("content", ""))[:300],
            "multimedia": parsed_mm,
        })
    elif isinstance(mm_val, list):
        # NEW: MULTIMEDIA is a list of dicts or strings
        for item in mm_val:
            if isinstance(item, dict):
                counter += 1
                blocks.append({
                    "id": f"img_{counter}",
                    "section": parent_key,
                    "section_content": str(obj.get("Content", "") or obj.get("content", ""))[:300],
                    "multimedia": _ensure_default_multimedia_type(item),
                })
            elif isinstance(item, str) and len(item.strip()) > 10:
                counter += 1
                blocks.append({
                    "id": f"img_{counter}",
                    "section": parent_key,
                    "section_content": str(obj.get("Content", "") or obj.get("content", ""))[:300],
                    "multimedia": _parse_multimedia_from_text(item),
                })
```

---

## Задача 3: Парсинг MULTIMEDIA из текстовых полей (Content, structura и т.д.)

**Файл:** `app/services/image_utils.py`

Добавить новые функции:

```python
import re

# Паттерны MULTIMEDIA тегов на разных языках для поиска в тексте
_MM_TEXT_TAGS = [
    # English
    "MULTIMEDIA", "IMAGE", "INFOGRAPHIC", "VISUAL",
    # Russian
    "МУЛЬТИМЕДИА", "ИЗОБРАЖЕНИЕ", "КАРТИНКА", "ИНФОГРАФИКА", "МЕДИА",
    # French
    "MULTIMÉDIA", "MÉDIA", "MÉDIAS", "INFOGRAPHIE",
    # German
    "MEDIEN", "BILD", "GRAFIK",
    # Spanish
    "IMAGEN", "MEDIO", "INFOGRAFÍA",
    # Italian
    "IMMAGINE",
    # Polish
    "OBRAZ", "GRAFIKA",
]

# Compiled regex for bracket patterns: [MULTIMEDIA: ...], [МУЛЬТИМЕДИА: ...], etc.
_BRACKET_TAGS = "|".join(re.escape(tag) for tag in _MM_TEXT_TAGS)
_BRACKET_PATTERN = re.compile(
    rf'\[(?:{_BRACKET_TAGS})(?:_\d+)?\s*:\s*(.+?)\]',
    re.IGNORECASE | re.DOTALL
)

# Compiled regex for bold/markdown patterns: **MULTIMEDIA**: ..., **МУЛЬТИМЕДИА**: ...
_BOLD_PATTERN = re.compile(
    rf'\*\*(?:{_BRACKET_TAGS})(?:_\d+)?\*\*\s*[:—\-]\s*(.+?)(?:\n\n|\n(?=[A-Z#*\[])|$)',
    re.IGNORECASE | re.DOTALL
)

# Compiled regex for dash patterns: MULTIMEDIA — ..., МУЛЬТИМЕДИА — ...
_DASH_PATTERN = re.compile(
    rf'(?:^|\n)\s*(?:{_BRACKET_TAGS})(?:_\d+)?\s*[—\-:]+\s*(.+?)(?:\n|$)',
    re.IGNORECASE | re.MULTILINE
)

# Type-bracket patterns: [Image: ...], [Infographic: ...], [Инфографика: ...]
_TYPE_NAMES = [
    "Image", "Infographic", "Infographie", "Infografía",
    "Изображение", "Инфографика", "Картинка",
    "Bild", "Grafik", "Immagine", "Imagen", "Obraz",
]
_TYPE_BRACKET_PATTERN = re.compile(
    rf'\[({"|".join(re.escape(t) for t in _TYPE_NAMES)})\s*:\s*(.+?)\]',
    re.IGNORECASE
)


def _parse_multimedia_from_text(text: str) -> dict:
    """
    Parse a text string that describes a multimedia element.
    Tries to extract Type and Description from free-form text.
    
    Examples:
    - "Infographic showing bonus tiers with percentages"
    - "Type: Image, Description: Abstract casino dashboard"  
    - "Инфографика — пошаговая схема регистрации"
    - "Image — hero visual of slot machines"
    """
    text = text.strip()
    result = {"Type": "Image", "Description": text, "Purpose": ""}
    
    # Try structured format: "Type: Image, Description: ..."
    type_match = re.search(
        r'[Tt]ype\s*[:=]\s*(Image|Infographic|Infographie|Инфографика|Изображение|Bild|Imagen|Immagine)',
        text, re.IGNORECASE
    )
    if type_match:
        result["Type"] = type_match.group(1).strip()
        text = text[:type_match.start()] + text[type_match.end():]
    else:
        # Check if text starts with type keyword (any language)
        text_lower = text.lower()
        type_starters = {
            "infographic": "Infographic", "infographie": "Infographic",
            "инфографика": "Infographic", "infografía": "Infographic",
            "image": "Image", "изображение": "Image", "картинка": "Image",
            "bild": "Image", "imagen": "Image", "immagine": "Image",
            "obraz": "Image", "grafika": "Infographic",
            "tableau": "Image", "schéma": "Infographic", "схема": "Infographic",
        }
        for starter, mm_type in type_starters.items():
            if text_lower.startswith(starter):
                result["Type"] = mm_type
                # Remove the type word from the beginning
                text = text[len(starter):].lstrip(" :—-–,.")
                break
    
    # Extract Description
    desc_match = re.search(r'[Dd]escription\s*[:=]\s*(.+?)(?:\.|,\s*[A-Z]|$)', text, re.DOTALL)
    if desc_match:
        result["Description"] = desc_match.group(1).strip()
    else:
        result["Description"] = re.sub(r'^[\s,\-—:]+', '', text).strip()
    
    # Extract Purpose
    purpose_match = re.search(r'[Pp]urpose\s*[:=]\s*(.+?)(?:\.|$)', text, re.DOTALL)
    if purpose_match:
        result["Purpose"] = purpose_match.group(1).strip()
    
    if not result["Description"]:
        result["Description"] = text[:200]
    
    return _ensure_default_multimedia_type(result)


def _extract_multimedia_from_text_content(text: str, parent_key: str) -> list:
    """
    Scan a text string (Content field value) for embedded MULTIMEDIA references
    in any supported language.
    
    Supported patterns:
    - [MULTIMEDIA: description] / [МУЛЬТИМЕДИА: описание]
    - **MULTIMEDIA**: description / **МУЛЬТИМЕДИА**: описание
    - MULTIMEDIA — description / МУЛЬТИМЕДИА — описание
    - [Image: description] / [Инфографика: описание]
    """
    results = []
    seen_descriptions = set()  # Deduplicate
    
    def _add_result(parsed_mm: dict):
        desc_key = parsed_mm.get("Description", "")[:50]
        if desc_key and desc_key not in seen_descriptions:
            seen_descriptions.add(desc_key)
            results.append({
                "id": "",  # will be set by caller
                "section": parent_key,
                "section_content": text[:300],
                "multimedia": parsed_mm,
            })
    
    # Pattern 1: [MULTIMEDIA: ...] / [МУЛЬТИМЕДИА: ...] etc.
    for match in _BRACKET_PATTERN.finditer(text):
        _add_result(_parse_multimedia_from_text(match.group(1)))
    
    # Pattern 2: **MULTIMEDIA**: ... / **МУЛЬТИМЕДИА**: ...
    for match in _BOLD_PATTERN.finditer(text):
        _add_result(_parse_multimedia_from_text(match.group(1).strip()))
    
    # Pattern 3: [Image: ...] / [Инфографика: ...]
    for match in _TYPE_BRACKET_PATTERN.finditer(text):
        mm_type = match.group(1).strip()
        desc = match.group(2).strip()
        _add_result(_ensure_default_multimedia_type({
            "Type": mm_type,
            "Description": desc,
            "Purpose": f"Visual element for '{parent_key}'",
        }))
    
    # Pattern 4: MULTIMEDIA — ... / МУЛЬТИМЕДИА — ...
    for match in _DASH_PATTERN.finditer(text):
        desc_text = match.group(1).strip()
        if len(desc_text) > 10:
            _add_result(_parse_multimedia_from_text(desc_text))
    
    return results
```

---

## Задача 4: Обновить _walk() для сканирования текстовых полей

**Файл:** `app/services/image_utils.py`, внутри `extract_multimedia_blocks`

В функции `_walk`, после обработки `mm_keys`, добавить сканирование строковых значений:

```python
def _walk(obj, parent_key="root"):
    nonlocal counter
    if isinstance(obj, dict):
        # === 1. Process MULTIMEDIA keys (existing + enhanced) ===
        mm_keys = [k for k in obj.keys() if _is_multimedia_key(k)]
        for mm_key in mm_keys:
            # ... (код из Задачи 2 — dict/string/list обработка)

        # === 2. NEW: Scan string values for embedded MULTIMEDIA text ===
        for key, value in obj.items():
            if _is_multimedia_key(key):
                continue  # Already processed above
            
            if isinstance(value, str) and len(value) > 30:
                text_blocks = _extract_multimedia_from_text_content(value, parent_key)
                for tb in text_blocks:
                    counter += 1
                    tb["id"] = f"img_{counter}"
                    blocks.append(tb)
            elif isinstance(value, (dict, list)):
                _walk(value, parent_key=key)
    
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, parent_key=parent_key)
```

**ВАЖНО:** Рекурсию в dict/list нужно делать только для значений, которые НЕ являются multimedia-ключами и НЕ являются строками (строки сканируем на текстовые паттерны, а не рекурсируем внутрь).

---

## Задача 5: Fallback в pipeline.py

**Файл:** `app/services/pipeline.py`, функция `phase_image_prompt_gen`

После строки `multimedia_blocks = extract_multimedia_blocks(outline_json)`:

```python
multimedia_blocks = extract_multimedia_blocks(outline_json)

# FALLBACK: если JSON-парсинг не нашёл MULTIMEDIA, поискать в raw тексте
if not multimedia_blocks and outline_raw and len(outline_raw) > 100:
    from app.services.image_utils import _extract_multimedia_from_text_content
    text_blocks = _extract_multimedia_from_text_content(outline_raw, "outline_raw")
    if text_blocks:
        for i, tb in enumerate(text_blocks, start=1):
            tb["id"] = f"img_{i}"
        multimedia_blocks = text_blocks
        add_log(
            ctx.db, ctx.task,
            f"Found {len(text_blocks)} MULTIMEDIA block(s) via raw text fallback "
            f"(not in JSON keys)",
            level="info", step=STEP_IMAGE_PROMPT_GEN,
        )

# Debug log if still nothing found
if not multimedia_blocks:
    outline_snippet = str(outline_raw)[:1500] if outline_raw else "EMPTY"
    add_log(
        ctx.db, ctx.task,
        f"[DEBUG] No MULTIMEDIA found anywhere. "
        f"Outline snippet (first 1500 chars): {outline_snippet}",
        level="warn", step=STEP_IMAGE_PROMPT_GEN,
    )
```

---

## Задача 6: Тесты

**Файл:** `tests/test_image_utils.py`

Добавить:

```python
def test_extract_multimedia_russian_key():
    """Russian МУЛЬТИМЕДИА key as dict."""
    outline = {
        "Section": {
            "Content": "Текст секции",
            "МУЛЬТИМЕДИА": {
                "Type": "Image",
                "Description": "Абстрактная визуализация бонусов",
                "Purpose": "Иллюстрация к секции",
            }
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert "бонусов" in blocks[0]["multimedia"]["Description"]


def test_extract_multimedia_russian_key_as_string():
    """Russian МУЛЬТИМЕДИА key with string value."""
    outline = {
        "Section": {
            "Content": "Текст",
            "МУЛЬТИМЕДИА": "Инфографика — пошаговая схема регистрации на сайте"
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert blocks[0]["multimedia"]["Type"] == "Infographic"
    assert "регистрации" in blocks[0]["multimedia"]["Description"]


def test_extract_multimedia_french_key():
    """French MULTIMÉDIA key."""
    outline = {
        "Section": {
            "Content": "Texte",
            "MULTIMÉDIA": {
                "Type": "Infographie",
                "Description": "Schéma des étapes d'inscription",
            }
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1


def test_extract_multimedia_russian_text_in_content():
    """Russian МУЛЬТИМЕДИА embedded in Content text."""
    outline = {
        "H2": "Бонусы",
        "Content": "Описание бонусов. [МУЛЬТИМЕДИА: Инфографика — сравнение бонусных программ] Продолжение текста."
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert "бонусных" in blocks[0]["multimedia"]["Description"]


def test_extract_multimedia_french_text_in_content():
    """French [MULTIMÉDIA: ...] in Content."""
    outline = {
        "H2": "Inscription",
        "Content": "Processus d'inscription. [MULTIMÉDIA: Infographie montrant les 3 étapes] Suite."
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1


def test_extract_multimedia_string_value():
    """MULTIMEDIA key exists but value is a string, not dict."""
    outline = {
        "H2": "Bonus Section",
        "Content": "Text about bonuses",
        "MULTIMEDIA": "Infographic showing bonus tiers with percentages and icons"
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert blocks[0]["multimedia"]["Type"] == "Infographic"


def test_extract_multimedia_from_content_brackets():
    """MULTIMEDIA embedded in Content as [MULTIMEDIA: ...]."""
    outline = {
        "H2": "Login",
        "Content": "Steps. [MULTIMEDIA: Infographic — step-by-step visual showing 3 login steps] More."
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1


def test_extract_multimedia_image_description_key():
    """Alternative key: image_description."""
    outline = {
        "H2": "Games",
        "Content": "About games",
        "image_description": "Hero visual of slot machine reels with glowing symbols"
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert "slot machine" in blocks[0]["multimedia"]["Description"].lower()


def test_extract_multimedia_изображение_key():
    """Russian key 'изображение'."""
    outline = {
        "Section": {
            "Content": "Текст",
            "изображение": "Абстрактный щит безопасности с неоновыми акцентами"
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1


def test_extract_multimedia_mixed_languages():
    """Mix of English dict and Russian text MULTIMEDIA."""
    outline = {
        "Section1": {
            "Content": "English text",
            "MULTIMEDIA": {
                "Type": "Image",
                "Description": "Proper dict image"
            }
        },
        "Section2": {
            "Content": "Русский текст [МУЛЬТИМЕДИА: Картинка — визуализация процесса оплаты]"
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 2


def test_extract_multimedia_list_value():
    """MULTIMEDIA as list of dicts."""
    outline = {
        "Section": {
            "Content": "Text",
            "MULTIMEDIA": [
                {"Type": "Image", "Description": "First image"},
                {"Type": "Infographic", "Description": "Second infographic"}
            ]
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 2
```

---

## Порядок выполнения

1. Обновить `app/services/image_utils.py`:
   - Добавить `MULTIMEDIA_KEY_VARIANTS`, `_is_multimedia_key()`
   - Добавить `_MM_TEXT_TAGS`, скомпилированные regex-паттерны
   - Добавить `_parse_multimedia_from_text()`
   - Добавить `_extract_multimedia_from_text_content()`
   - Обновить `_walk()` внутри `extract_multimedia_blocks()`
2. Обновить `app/services/pipeline.py` → `phase_image_prompt_gen` — добавить raw text fallback
3. Добавить тесты в `tests/test_image_utils.py`
4. Запустить тесты: `python -m pytest tests/test_image_utils.py -v`
5. Перезапустить: `docker-compose restart worker web`
6. Retry задачу с cascade от `image_prompt_generation`

---

## Чеклист

- [ ] Парсер находит `MULTIMEDIA` (English dict) — существующие тесты проходят
- [ ] Парсер находит `МУЛЬТИМЕДИА` (Russian dict)
- [ ] Парсер находит `MULTIMÉDIA` (French dict)
- [ ] Парсер находит `MULTIMEDIA` со строковым значением
- [ ] Парсер находит `МУЛЬТИМЕДИА` со строковым значением
- [ ] Парсер находит `[MULTIMEDIA: ...]` в тексте Content
- [ ] Парсер находит `[МУЛЬТИМЕДИА: ...]` в тексте Content
- [ ] Парсер находит `[MULTIMÉDIA: ...]` в тексте Content
- [ ] Парсер находит ключи `image_description`, `visual`, `изображение`
- [ ] Парсер находит `MULTIMEDIA` как list (массив)
- [ ] Fallback в pipeline: raw text scan если JSON-парсинг 0 блоков
- [ ] Debug-лог при 0 блоках
- [ ] Все 6 существующих тестов проходят
- [ ] Все новые тесты проходят
- [ ] Тестовая задача: image_prompt_generation находит блоки
