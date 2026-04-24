# Plan: Fix Project page errors (NUL bytes in scrape, OpenRouter 402 on oversized max_tokens)

## Context

A Project run produced two page failures out of 9:

1. **Bonus (SERP/Scraping)** — `ValueError: A string literal cannot contain NUL (0x00) characters.` raised by the Postgres driver in [app/services/pipeline/steps/serp_step.py:170](app/services/pipeline/steps/serp_step.py:170) during `ctx.db.commit()`. The failing commit belongs to `ScrapingStep`, which writes `ctx.task.competitors_text = scrape_data["merged_text"]`. Scraped HTML sometimes contains NUL bytes that BeautifulSoup's `get_text()` preserves; Postgres TEXT/JSONB columns reject them.
2. **Login (Draft)** — OpenRouter HTTP `402 Payment Required`: `You requested up to 65536 tokens, but can only afford 53233`. Raised from [app/services/pipeline/llm_client.py:226](app/services/pipeline/llm_client.py:226) via [app/services/pipeline/steps/draft_step.py:35](app/services/pipeline/steps/draft_step.py:35). `max_tokens=65536` comes from a `Prompt` DB row (`max_tokens_enabled=True, max_tokens=65536`) resolved in [app/services/prompt_llm_kwargs.py](app/services/prompt_llm_kwargs.py). The current retry loop in [app/services/llm.py:185](app/services/llm.py:185) classifies 402 as "unknown", sleeps 5s, and retries the same oversized request — pointless and slow.

Desired outcome: these two failure modes should not kill a page. NUL bytes should be stripped at the ingestion boundary, and oversized-vs-credits should either auto-downscale on the retry or fail fast with a clear error (no redundant retry of a hopeless request).

## Proposed changes

### Fix 1 — Strip NUL bytes from scraped text and SERP data before DB write

**Where to sanitize.** Sanitize at the two ingress boundaries where external strings flow into DB columns (`Task.competitors_text` TEXT, `Task.serp_data` JSONB, `Task.outline` JSONB):

- [app/services/scraper.py](app/services/scraper.py) — in `parse_html()` (the function at the top of the file), strip NULs from `text`, `meta_title`, `meta_description`, and all `headers[...]` entries before returning. This covers `merged_text` as well as `headers_structure` that ends up in `Task.outline["scrape_info"]["headers"]`.
- [app/services/pipeline/steps/serp_step.py](app/services/pipeline/steps/serp_step.py) — in `SerpStep.run()`, sanitize `serp_data` recursively right before `ctx.task.serp_data = serp_data` at [serp_step.py:68](app/services/pipeline/steps/serp_step.py:68). Serper.dev results contain titles/snippets/AI overview text that can carry NUL bytes too.

**Helper.** No NUL-stripping utility exists in the repo (verified by grep). Add one small helper and reuse it in both places. Good home: extend the existing util module if there is one for text, otherwise drop it next to the code that uses it. Proposed signature:

```python
def strip_nul(value):
    """Recursively remove NUL (0x00) bytes from strings inside dict/list/str; passthrough for other types."""
```

Keep it minimal — no regex, just `str.replace("\x00", "")`. Apply recursively into dicts and lists so JSONB payloads are covered in one call.

**Why not sanitize at the SQLAlchemy layer** (e.g. a TypeDecorator): more invasive, changes behavior globally, and we only have two entry points. Ingress-side sanitization is local, cheap, and easy to reason about.

### Fix 2 — Handle OpenRouter 402 "can only afford N tokens" gracefully

**Two-part fix** in [app/services/llm.py](app/services/llm.py) (and a small signal in [app/services/pipeline/llm_client.py](app/services/pipeline/llm_client.py)):

1. **Parse the 402 affordance message** in the retry loop around [llm.py:185-215](app/services/llm.py:185). When the error string contains `402` and `can only afford`, extract the integer via regex (`can only afford (\d+)`). If extracted and smaller than the current `max_tokens`:
   - On retry, reduce `max_tokens` to `affordable - 256` (small safety margin; never below a floor like 1024 — below that, fail out).
   - Skip the 5s sleep for this case (the problem isn't transient).
   - Log the downscale clearly so the user can see the pipeline adapted.
2. **Fail fast on unfixable 402** (no affordance number, or already at the floor). Raise a distinct exception — either a new `InsufficientCreditsError` subclass of `LLMError` in [app/services/pipeline/errors.py](app/services/pipeline/errors.py), or at minimum raise `LLMError("Insufficient OpenRouter credits: ...")` immediately instead of looping. This surfaces a clean message in the per-page `error` field and avoids 2 × 5s pointless retries.

**Do not** touch the Prompt-row DB config as part of this change. The fix must work even if the row keeps `max_tokens=65536`; the user can lower it separately if they prefer.

**Test plan (manual, since no test suite wiring for LLM calls):**
- Unit-level: add a small test that feeds a fake 402 error string through the retry path and asserts that `max_tokens` is reduced on the next attempt. (Optional; the retry loop is currently not covered by tests — decide with user whether to add.)
- Integration: replay the failing project on the same keywords after applying fix; Login page should either succeed with downscaled tokens or fail fast with `InsufficientCreditsError` and a clean message.

## Critical files

- [app/services/scraper.py](app/services/scraper.py) — sanitize in `parse_html()`.
- [app/services/pipeline/steps/serp_step.py](app/services/pipeline/steps/serp_step.py) — sanitize `serp_data` before commit at line 68.
- [app/services/llm.py](app/services/llm.py) — 402 detection + max_tokens downscale + no-retry fast-fail (lines 185-221).
- [app/services/pipeline/errors.py](app/services/pipeline/errors.py) — optional `InsufficientCreditsError(LLMError)` subclass.
- [app/services/pipeline/llm_client.py](app/services/pipeline/llm_client.py) — propagate the new error type unchanged (the existing `except Exception → LLMError` wrapper at line 228 should preserve the subclass or be adjusted to re-raise credits errors with a clearer message).

## Verification

1. Unit-ish: write a tiny script or ad-hoc test that calls `parse_html("<p>abc\x00def</p>")` and confirms output has no NULs.
2. Unit-ish: simulate a 402 response-string in the `generate_text` retry path and confirm the retry uses `max_tokens = affordable - 256`.
3. End-to-end: re-run the same project (`golden tiger`, Bonus + Login pages). Bonus should complete scraping without the NUL error; Login should either complete with downscaled tokens or fail with a clear `Insufficient credits` message — not a 500-line traceback.
4. Check `task.serp_data` and `task.competitors_text` for the re-run in DB; confirm no `\x00` bytes via a quick query.

## Out of scope

- Changing the seeded `max_tokens=65536` value in the Prompt row — that is a data/config decision for the user, not part of this fix.
- Adding a pre-flight OpenRouter credit balance check before each LLM call — larger change, and the 402 handler above is sufficient.
- Refactoring the retry loop's error-classification logic beyond adding the 402 branch.
