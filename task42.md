# Этап 2: Декомпозиция `app/services/pipeline.py`

## Context

[app/services/pipeline.py](app/services/pipeline.py) разросся до **2579 строк** и совмещает пять несвязанных обязанностей: оркестрация (runner, timeout, pause/resume, heartbeat), 21 phase-функция разных доменов (SERP, контент, картинки, legal, HTML, meta), построение `PipelineContext`, подготовку `analysis_vars`/`template_vars`, сборку и сохранение итогового `GeneratedArticle`. Любое изменение одного шага заставляет перечитывать весь файл; новые шаги вливаются в монолит; тесты на отдельные шаги писать неудобно. `from pipeline_constants import *` ([pipeline.py:28](app/services/pipeline.py:28)) прячет 24+ имени и мешает IDE-навигации.

**Цель:** превратить `pipeline.py` в пакет `app/services/pipeline/` с чёткими модулями, каждый ≤ 400 строк, с единым step-interface, изолированным runner-ом, типизированным контекстом и иерархией ошибок. Поведение пайплайна менять нельзя — это чисто структурный рефакторинг.

**Критерий готовности:** ни один файл в `app/services/pipeline/` > 400 строк; `pytest` (все существующие тесты) проходит; реальный запуск задачи через worker воспроизводит текущий артефакт.

---

## Текущая карта (по данным Explore)

- **Runner**: `run_pipeline` ([pipeline.py:2270–2579](app/services/pipeline.py:2270)) + `run_phase` ([pipeline.py:932–967](app/services/pipeline.py:932)) — timeout через `signal`, pause/resume (`_pipeline_pause`, `image_review`, `serp_review`, `test_mode`), авто-approve картинок, финальная сборка/сохранение `GeneratedArticle`.
- **Phase-функции** (21 шт.), зарегистрированы в `PHASE_REGISTRY` ([pipeline.py:2197–2219](app/services/pipeline.py:2197)):
  - SERP+scraping: `phase_serp`, `phase_scraping` ([969–1088](app/services/pipeline.py:969))
  - Structure/outline: `phase_ai_structure`, `phase_chunk_analysis`, `phase_competitor_structure`, `phase_final_structure`, `phase_structure_fact_check` ([1089–1201](app/services/pipeline.py:1089))
  - Images: `phase_image_prompt_gen`, `phase_image_gen`, `phase_image_inject` ([1202–1785](app/services/pipeline.py:1202)) — 584 строк, самая крупная группа
  - Draft/content: `phase_primary_gen`, `phase_primary_gen_about`, `phase_primary_gen_legal`, `phase_competitor_comparison`, `phase_reader_opinion`, `phase_interlink`, `phase_improver` ([1786–1944](app/services/pipeline.py:1786))
  - Post-processing: `phase_final_editing`, `phase_html_structure`, `phase_content_fact_check`, `phase_meta_generation` ([1945–2221](app/services/pipeline.py:1945))
- **Context / vars setup**: `PipelineContext.__init__` ([40–84](app/services/pipeline.py:40)), `setup_vars` ([531–803](app/services/pipeline.py:531)), `setup_template_vars` ([805–930](app/services/pipeline.py:805))
- **LLM / persistence helpers**: `call_agent`, `call_agent_with_exclude_validation` ([243–521](app/services/pipeline.py:243)), `save_step_result`, `mark_step_running`, `add_log` ([94–158](app/services/pipeline.py:94)), `apply_template_vars` ([209–241](app/services/pipeline.py:209))
- **Assembly**: `pick_structured_html_for_assembly`, `pick_html_for_meta` ([171–204](app/services/pipeline.py:171)), финальный блок в `run_pipeline` ([2436–2562](app/services/pipeline.py:2436))
- **Callers**: `app/workers/tasks.py` (импортирует `run_pipeline`), `app/api/prompts.py` (импортирует `apply_template_vars`).
- **DOCX**: отдельный модуль [docx_builder.py](app/services/docx_builder.py); в текущем пайплайне **не шаг**, вызывается постфактум. В новой структуре делаем под него место как опциональный шаг (файл создаётся, но пока only-stub / адаптер).

---

## Целевая структура пакета

```
app/services/pipeline/
├── __init__.py            # публичный re-export: run_pipeline, PipelineContext, apply_template_vars
├── context.py             # PipelineContext + типизированные геттеры step-output
├── registry.py            # STEP_REGISTRY + resolve_pipeline_steps_from_preset
├── runner.py              # run_pipeline + run_phase + pause/resume + timeout
├── assembly.py            # финальная сборка GeneratedArticle (pick_*, extract_meta, save)
├── persistence.py         # save_step_result, mark_step_running, add_log, _completed_step_body
├── vars.py                # setup_vars + setup_template_vars + apply_template_vars
├── llm_client.py          # call_agent, call_agent_with_exclude_validation, get_prompt_obj
├── errors.py              # PipelineError hierarchy
└── steps/
    ├── __init__.py        # импорт всех шагов, чтобы регистрация через декоратор сработала
    ├── base.py            # PipelineStep Protocol, StepResult, StepPolicy
    ├── serp_step.py       # phase_serp + phase_scraping
    ├── outline_step.py    # structure/outline (5 шагов)
    ├── image_prompts_step.py  # phase_image_prompt_gen
    ├── image_gen_step.py  # phase_image_gen + auto-approve helper
    ├── image_inject_step.py   # phase_image_inject
    ├── draft_step.py      # primary_generation, about, comparison, reader_opinion, interlink, improver
    ├── legal_step.py      # primary_generation_legal
    ├── final_editing_step.py  # phase_final_editing
    ├── html_assembly_step.py  # phase_html_structure + fact_check
    ├── meta_step.py       # phase_meta_generation
    └── docx_step.py       # адаптер вокруг docx_builder (опциональный шаг; пока no-op если выключен)
```

Почему так, а не «один файл на один шаг»: 21 файл на 21 шаг раздробит тесно связанную логику (все primary_generation_* шагов пользуются одним шаблоном prompt+save). Группируем по домену и при этом соблюдаем цель ≤ 400 строк (самая большая группа — images, она уже разбита на 3 файла).

---

## Интерфейс шага

[steps/base.py](app/services/pipeline/steps/base.py):

```python
from typing import Protocol, Callable
from dataclasses import dataclass, field
from .errors import PipelineError

@dataclass
class StepResult:
    status: str                 # "completed" | "completed_with_warnings" | "skipped"
    result: str | None = None
    model: str | None = None
    cost: float = 0.0
    variables_snapshot: dict | None = None
    resolved_prompts: dict | None = None
    extra: dict = field(default_factory=dict)   # exclude_words_violations, word counts, etc.

@dataclass
class StepPolicy:
    retryable_errors: tuple[type[PipelineError], ...] = ()
    max_retries: int = 0
    skip_on: tuple[type[PipelineError], ...] = ()
    timeout_minutes: int | None = None   # None => settings.STEP_TIMEOUT_MINUTES

class PipelineStep(Protocol):
    name: str
    policy: StepPolicy
    def run(self, ctx: "PipelineContext") -> StepResult: ...
```

**Регистрация** через декоратор в [registry.py](app/services/pipeline/registry.py):

```python
STEP_REGISTRY: dict[str, PipelineStep] = {}

def register_step(step: PipelineStep) -> PipelineStep:
    STEP_REGISTRY[step.name] = step
    return step
```

Каждый файл `steps/*.py` импортируется в `steps/__init__.py`, side-effect — регистрация. Runner смотрит в `STEP_REGISTRY`, `PHASE_REGISTRY` уходит.

---

## Типизированный `PipelineContext`

[context.py](app/services/pipeline/context.py): оставляем существующие поля (`db`, `task`, `site`, `blueprint_page`, `page_slug`, `page_title`, `analysis_vars`, `template_vars`, `outline_data`, `auto_mode`, `pipeline_steps`) и добавляем **типизированное API** для чтения прошлых шагов:

```python
def step_output(self, key: str) -> str:
    """Stripped body of a completed step or ''. Replaces ad-hoc task.step_results[key]['result']."""

@property
def serp(self) -> str:      return self.step_output(STEP_SERP)
@property
def outline(self) -> str:   return self.step_output(STEP_FINAL_ANALYSIS)
@property
def draft(self) -> str:     return self.step_output(STEP_PRIMARY_GEN)
@property
def html(self) -> str:      return self.step_output(STEP_HTML_STRUCT)
@property
def meta_raw(self) -> str:  return self.step_output(STEP_META_GEN)
```

Под капотом `step_output` использует существующий `_completed_step_body` (переезжает в `persistence.py`). Внутри steps запрещаем `ctx.task.step_results[...]` — линтерная проверка на этапе code-review.

---

## Иерархия ошибок

[errors.py](app/services/pipeline/errors.py):

```python
class PipelineError(Exception): ...
class LLMError(PipelineError): ...              # generate_text failure, rate limit
class SerpError(PipelineError): ...             # fetch_serp_data failure
class ScrapingError(PipelineError): ...
class ParseError(PipelineError): ...            # clean_and_parse_json failure
class ValidationError(PipelineError): ...       # missing critical vars, empty HTML
class BudgetExceededError(PipelineError): ...   # max cost / max iterations
class StepTimeoutError(PipelineError): ...      # replaces raw TimeoutError
```

- Steps **бросают** эти ошибки вместо `Exception(...)` / `ValueError(...)`.
- Runner в `run_phase` ловит `PipelineError`, смотрит `step.policy`:
  - если `type(err) in policy.retryable_errors` и попыток осталось → retry с backoff;
  - если `type(err) in policy.skip_on` → log warn, save `status=skipped`, continue;
  - иначе → save `status=failed`, re-raise → верхний уровень помечает task failed.
- `call_agent` / `generate_text` / `fetch_serp_data` оборачиваются тонкими адаптерами в `llm_client.py` / `steps/serp_step.py`, чтобы мапить нижние исключения в `LLMError` / `SerpError`.

**Важно:** не меняем поведение существующей retry-логики LLM (`llm.py`) — она работает на уровне вызова модели. Новая иерархия живёт выше: на уровне шага.

---

## План миграции (инкрементально, с сохранением поведения)

Каждый подшаг — отдельный коммит, green tests после каждого.

### Шаг 0 — инвентаризация и тесты-якорь (0.5 дня)
- Прогнать `pytest tests/services/test_pipeline_smoke.py` как baseline.
- Добавить smoke-тест: `run_pipeline` на синтетическом Task с замоканными `generate_text`/`fetch_serp_data`, проверяем, что по всем 21 шагу последовательно появились записи в `step_results` и создался `GeneratedArticle`. Этот тест — страховка на всю миграцию.

### Шаг 1 — пакет + пустой re-export (0.5 дня)
- Создать `app/services/pipeline/__init__.py`; там пока `from app.services._pipeline_legacy import *`.
- Переименовать `app/services/pipeline.py` → `app/services/_pipeline_legacy.py` (физический файл не трогаем содержимым).
- Убедиться, что `app/workers/tasks.py` и `app/api/prompts.py` импортируют из `app.services.pipeline` — это уже так, сломаться не должно.
- Прогнать smoke + existing tests.

### Шаг 2 — вынос persistence + vars + llm_client (1 день)
- Перенести в [persistence.py](app/services/pipeline/persistence.py): `save_step_result`, `mark_step_running`, `add_log`, `_completed_step_body`.
- Перенести в [vars.py](app/services/pipeline/vars.py): `setup_vars`, `setup_template_vars`, `apply_template_vars`.
- Перенести в [llm_client.py](app/services/pipeline/llm_client.py): `get_prompt_obj`, `call_agent`, `call_agent_with_exclude_validation`.
- В `_pipeline_legacy.py` заменить определения на `from .persistence import *` и т.д. (тонкий shim).
- В `__init__.py` явно реэкспортируем `apply_template_vars` (использует `app/api/prompts.py`).
- Заменить `from app.services.pipeline_constants import *` на явный список — одно место, [_pipeline_legacy.py:28](app/services/pipeline.py:28).

### Шаг 3 — базовый интерфейс + registry + errors (0.5 дня)
- Создать `steps/base.py` (`PipelineStep`, `StepResult`, `StepPolicy`), `registry.py`, `errors.py`.
- Пока без переноса шагов — runner продолжает использовать `PHASE_REGISTRY` из legacy.

### Шаг 4 — вынос PipelineContext + assembly (1 день)
- [context.py](app/services/pipeline/context.py) — PipelineContext + типизированные геттеры.
- [assembly.py](app/services/pipeline/assembly.py) — `pick_structured_html_for_assembly`, `pick_html_for_meta`, финальный блок сборки (линии 2436–2562) как функция `finalize_article(ctx) -> GeneratedArticle`.
- Runner в legacy вызывает `finalize_article`.

### Шаг 5 — перенос шагов (2–3 дня, по одной группе за коммит)
Порядок — от самых изолированных к самым переплетённым:
1. `serp_step.py` — phase_serp, phase_scraping
2. `outline_step.py` — 5 structure-шагов
3. `meta_step.py` — phase_meta_generation (почти независим)
4. `html_assembly_step.py` — phase_html_structure + phase_content_fact_check
5. `final_editing_step.py` — phase_final_editing
6. `image_prompts_step.py`, `image_gen_step.py`, `image_inject_step.py` — 3 коммита, самый тонкий кусок (pause-логика `image_review` переезжает в runner-level hook)
7. `draft_step.py` — 7 шагов primary_generation*/comparison/opinion/interlink/improver
8. `legal_step.py` — primary_generation_legal (отдельно т.к. инъекция legal template vars специфична)
9. `docx_step.py` — no-op stub + адаптер к `docx_builder`

Для каждой группы:
- Скопировать phase-функцию в класс `class SerpStep: name = STEP_SERP; policy = StepPolicy(...); def run(self, ctx): ...`
- Возвращать `StepResult` вместо прямого `save_step_result` — запись делает runner после успешного return.
- В `_pipeline_legacy.py` удалить перенесённую phase-функцию; в `PHASE_REGISTRY` вместо неё адаптер `lambda ctx: _run_as_legacy(STEP_REGISTRY[key], ctx)`.
- Прогон smoke + целевые тесты; diff итогового `step_results` с baseline должен быть пустым.

### Шаг 6 — новый runner (1 день)
- [runner.py](app/services/pipeline/runner.py): `run_pipeline(db, task_id, auto_mode)` + приватный `_run_phase(ctx, step: PipelineStep)`:
  - timeout через `signal` (логика из legacy `run_phase`)
  - mark_step_running → step.run() → save_step_result(status=completed, extra=step_result.extra)
  - retry/skip по `step.policy`
  - heartbeat через `save_step_result` (сохраняется — `task.last_heartbeat` уже там)
- Pause/resume логика (`_pipeline_pause`, `image_review`, `serp_review`, `test_mode`) остаётся в runner-е как отдельные функции `_handle_pause_on_entry`, `_handle_pause_after_step(step_name, ctx)`. Не выносим в шаги — это cross-cutting concern.
- `PHASE_REGISTRY` удаляется; runner читает `STEP_REGISTRY`.
- `_pipeline_legacy.py` удаляется целиком.

### Шаг 7 — финальная чистка (0.5 дня)
- Убрать shim-реэкспорты, если остались.
- Проверить размеры всех файлов `wc -l app/services/pipeline/**/*.py` — все ≤ 400.
- Полный прогон `pytest`.
- Ручной прогон одной задачи через worker (SERP+draft+HTML), сверить итоговый `GeneratedArticle.full_page_html` с baseline до миграции.

---

## Критические файлы, затронутые миграцией

- [app/services/pipeline.py](app/services/pipeline.py) — удаляется в конце, превращается в пакет
- [app/services/pipeline_constants.py](app/services/pipeline_constants.py) — без изменений, только явный импорт взамен `*`
- [app/services/pipeline_presets.py](app/services/pipeline_presets.py) — без изменений, runner продолжает звать `resolve_pipeline_steps`
- [app/workers/tasks.py](app/workers/tasks.py) — импорт `run_pipeline` продолжает работать через `pipeline/__init__.py`
- [app/api/prompts.py](app/api/prompts.py) — импорт `apply_template_vars` через `pipeline/__init__.py`
- [tests/services/test_pipeline_smoke.py](tests/services/test_pipeline_smoke.py) — дополнить end-to-end smoke, см. «Verification»

---

## Переиспользуемое (не создавать заново)

- LLM retry / cost tracking — уже в [llm.py](app/services/llm.py), не трогаем
- JSON парсинг — [json_parser.py](app/services/json_parser.py) `clean_and_parse_json`
- Meta extract — [meta_parser.py](app/services/meta_parser.py) `extract_meta_from_parsed`
- Word count — [word_counter.py](app/services/word_counter.py)
- Legal template vars — [legal_reference.py](app/services/legal_reference.py) `inject_legal_template_vars`
- Full page assembly — [template_engine.py](app/services/template_engine.py) `generate_full_page`
- Dedup anchors — [deduplication.py](app/services/deduplication.py) `ContentDeduplicator`
- Notifier — [notifier.py](app/services/notifier.py) `notify_task_success/failed`
- Pipeline presets — [pipeline_presets.py](app/services/pipeline_presets.py) `PIPELINE_PRESETS`, `pipeline_steps_use_serp`, `resolve_pipeline_steps`
- DOCX — [docx_builder.py](app/services/docx_builder.py), вызывается из `docx_step.py` как адаптер

---

## Verification

1. **Unit/smoke тесты:**
   - Существующий `tests/services/test_pipeline_smoke.py` — проходит.
   - Новый `tests/services/test_pipeline_e2e_smoke.py`: мокаем `generate_text`, `fetch_serp_data`, `scrape_urls`, `image_generator.*`, прогоняем полный `run_pipeline` на фикстуре `Task`+`Site`+`BlueprintPage`. Ассёрты:
     - все 21 шаг имеют `status=completed` в `task.step_results`
     - создан ровно один `GeneratedArticle` с непустыми `title`, `description`, `html_content`
     - `task.status == "completed"`
     - длина `task.log_events` > 0
   - Новый `tests/services/test_pipeline_errors.py`: фиксируем поведение `LLMError` (retry по policy), `ParseError` (skip), `ValidationError` (fail + task.status="failed").
2. **Размер файлов:** `find app/services/pipeline -name '*.py' -exec wc -l {} + | sort -n` — ни одной строки > 400.
3. **Регрессия на реальном запуске:** прогнать одну задачу через worker до и после рефакторинга, diff `GeneratedArticle.full_page_html` должен быть пустым (LLM-ответы зафиксировать через запись фикстур или сравнивать структуру, не содержимое).
4. **Импорт-грепы:** `rg 'from app.services.pipeline import' app` и `rg 'from app.services._pipeline_legacy' app` — второй пустой после шага 7.
5. **Тип-чек** (если проект использует mypy/pyright): `PipelineStep` Protocol соблюдается всеми реализациями шагов.

---

## Риски и их митигация

| Риск                                                                      | Митигация                                                                                                                                  |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Смена порядка побочных эффектов (commit/save) изменит поведение при сбоях | Runner вызывает `save_step_result` **после** `step.run()` возвращения, как и сейчас; `mark_step_running` — до. Сохраняем порядок коммитов. |
| Pause-логика cross-cutting, сложно вытащить из шагов images/SERP          | Оставляем в runner, шаги сигнализируют через `StepResult.extra["pause_reason"]`. Runner решает, паузить ли после шага.                     |
| `signal`-based timeout работает только в main thread                      | Не меняем механизм — текущий код так и работает (worker = main thread). Документируем в `runner.py`.                                       |
| `apply_template_vars` импортируется извне пакета                          | Реэкспорт через `app/services/pipeline/__init__.py`; `app/api/prompts.py` не меняется.                                                     |
| 2–3 недели рефакторинга под активной разработкой → merge-конфликты        | Каждый шаг в отдельном PR, идёт в main быстро; новые phase-функции, добавленные в процессе, сначала лендятся в legacy, потом переносятся.  |
| Поведение `TEST_MODE` и auto_mode тонко зависит от места pause-check      | Явные интеграционные тесты для обоих режимов с проверкой `status=paused` и `_pipeline_pause.active`.                                       |
