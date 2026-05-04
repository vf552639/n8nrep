#!/usr/bin/env python3
"""
One-off helper to split docs/CURRENT_STATUS.md into docs/changelog/*.md (task52).
Run from repo root: python scripts/split_current_status.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "CURRENT_STATUS.md"
OUT_DIR = ROOT / "docs" / "changelog"

# First six ### sections stay fully inlined in CURRENT_STATUS (newest operational changelog).
KEEP_FULL_TITLES = {
    "Май 2026 — task51: снижение egress Supabase (`task51.md`)",
    "Май 2026 — Blueprint: per-page `hide_author_geo` (футер автора, `task50.md`, commit `f4ff8d8`)",
    "Апрель 2026 — task60: security hardening API/infra",
    "Апрель 2026 — task59: `PendingRollbackError` после обрыва соединения к БД во время LLM",
    "Апрель 2026 — task58: нормализация `authors.country` в форме Authors",
    "Апрель 2026 — task55: exclude-words retries только в `final_editing`",
}

# ### under ## ✅ Выполнено that stay as bullet-structure (not extracted), except PIPELINE_OBS.
INVENTORY_TITLES = {
    "Инфраструктура",
    "Core Pipeline (шаги по пресету / custom)",
    "Опциональная Image Generation Цепочка (Midjourney)",
    "Pipeline-фичи",
    "Система проектов",
    "Админ-панель (React SPA)",
    "Уведомления",
}

TITLE_TO_FILE: dict[str, str] = {
    "Апрель 2026 — task54: NUL-санитизация и OpenRouter 402": "2026-04-task54-nul-sanitize-openrouter-402.md",
    "Апрель 2026 — task53 E: страницы проекта, БД-таймаут и диагностика ошибок": "2026-04-task53e-project-page-db-resilience.md",
    "Апрель 2026 — task52: зависания LLM-шагов, таймауты и revoke Celery": "2026-04-task52-llm-step-timeouts-revoke.md",
    "Апрель 2026 — task50: сверка плана после удаления legacy": "2026-04-task50-pipeline-followup.md",
    "Апрель 2026 — task48: стабилизация pipeline runner + e2e smoke": "2026-04-task48-pipeline-runner-stabilization.md",
    "Апрель 2026 — task45 (Шаг 4): Context + Assembly, статус": "2026-04-task45-context-assembly.md",
    "Апрель 2026 — task46: контракт `finalize_article` + unit-тесты": "2026-04-task46-finalize-article-contract.md",
    "Апрель 2026 — task47: аудит step-классов (без правок кода)": "2026-04-task47-step-classes-audit.md",
    "Апрель 2026 — task43: декомпозиция pipeline (A–E, F1–F10)": "2026-04-task43-pipeline-decomposition.md",
    "22 апреля 2026 — taskco: wire-up и quality gates": "2026-04-22-taskco-wireup-quality-gates.md",
    "22 апреля 2026 — task42: план декомпозиции pipeline.py": "2026-04-22-task42-pipeline-decomposition-plan.md",
    "23 апреля 2026 — Этап 1: task37 (API happy-path тесты)": "2026-04-23-task37-api-happy-path-tests.md",
    "19 апреля 2026 — Этап 1: фундамент качества (task36)": "2026-04-19-stage1-quality-foundation-task36.md",
    "22 апреля 2026 — Этап 1: доводка (tasks API, smoke-тесты, DoD 1.2)": "2026-04-22-stage1-tasks-api-smoke-dod12.md",
    "21 апреля 2026 — Legal: `primary_generation_legal`, inject, критичные переменные": "2026-04-21-legal-primary-generation-inject.md",
    "21 апреля 2026 — task41: пользовательские URL конкурентов для проекта": "2026-04-21-task41-project-competitor-urls.md",
    "20 апреля 2026 — Markup only: создание проекта без Target Site": "2026-04-20-markup-only-projects.md",
    "20 апреля 2026 — task40: гарантированные meta-теги и блок автора в финальном HTML": "2026-04-20-task40-meta-tags-author-footer.md",
    "19 апреля 2026 — HTML-экспорт страниц (MODX / Source)": "2026-04-19-html-export-modx.md",
    "19 апреля 2026 — Зависшие проекты: force-delete, массовое удаление, reset-status, каскад сайта": "2026-04-19-stuck-projects-force-delete.md",
    "18 апреля 2026 — Sites API и чекбокс Use site HTML template": "2026-04-18-sites-api-use-template-checkbox.md",
    "18 апреля 2026 — Language: INITCAP и защита на фронте": "2026-04-18-language-initcap-frontend.md",
    "18 апреля 2026 — Legal templates: дефолт на Blueprint, override в Project, фолбек в pipeline": "2026-04-18-legal-templates-blueprint-default.md",
    "18 апреля 2026 — LegalPageTemplate: удаление поля `title`": "2026-04-18-legal-page-template-drop-title.md",
    "18 апреля 2026 — Проект: `use_site_template` (обёртка сайта опционально)": "2026-04-18-project-use-site-template.md",
    "16 апреля 2026 — Защитная инфраструктура: 500 как JSON, миграции, пул БД, Alembic DDL": "2026-04-16-defensive-infra-500-json-alembic.md",
    "15 апреля 2026 — `phase_image_inject`: корректный инжект по `<!-- MEDIA: ... -->`": "2026-04-15-phase-image-inject-media-comments.md",
    "15 апреля 2026 — DOCX: тело статьи из шагов без «перехвата» `final_editing`": "2026-04-15-docx-body-without-final-editing.md",
    "14 апреля 2026 — SERP URL review: автопарсинг title/description + fallback в pipeline": "2026-04-14-serp-url-review-meta-autoparse.md",
    "13 апреля 2026 — Пауза после SERP: ревью и редактирование URL конкурентов": "2026-04-13-serp-url-review-pause.md",
    "11 апреля 2026 — JSON-парсер, `meta_generation`, Top P в Model Settings (UI)": "2026-04-11-json-parser-meta-generation-top-p.md",
    "8 апреля 2026 — LLM: не передавать `top_p` / penalties в API при `*_enabled = False`; Force Fail/Complete для `stale`": "2026-04-08-llm-no-top-p-penalties-when-disabled.md",
    "6 апреля 2026 — Pipeline Presets (набор шагов per страница блупринта)": "2026-04-06-pipeline-presets-per-page.md",
    "Апрель 2026 — Monaco для HTML: Article Review, Article Detail; ручное сохранение `step_results`": "2026-04-monaco-html-article-review.md",
    "Апрель 2026 — `llm.py`: стоимость и токены из сырого ответа OpenRouter; логи pipeline": "2026-04-llm-cost-tokens-from-raw.md",
    "Апрель 2026 — DOCX одиночной статьи/задачи: шапка H1 и строка Title в таблице": "2026-04-docx-single-article-h1-header.md",
    "Апрель 2026 — Model Settings: флаги `*_enabled` (task21), pipeline и гидратация UI": "2026-04-model-settings-enabled-flags.md",
    "3 апреля 2026 — Prompts: сохранение in-place, Model Settings UI, фикс выбора модели": "2026-04-03-prompts-save-in-place-model-settings.md",
    "2 апреля 2026 — Pipeline: контекст шага `final_editing`": "2026-04-02-pipeline-final-editing-context.md",
    "2 апреля 2026 — DOCX: одиночная статья и одиночная задача": "2026-04-02-docx-single-article-task.md",
    "2 апреля 2026 (вторая итерация) — Инфраструктура, API, React UI": "2026-04-02-infra-api-react-iteration2.md",
    "2 апреля 2026 — Проекты: DOCX, additional keywords, формат meta_generation": "2026-04-02-projects-docx-additional-keywords.md",
    "1 апреля 2026 — Templates, Legal Pages, связь Site → Template": "2026-04-01-templates-legal-pages-site-link.md",
    "31 марта 2026 — Pipeline Observability + Isolated Project Pages": "2026-03-31-pipeline-observability-isolated-pages.md",
    "Март 2026 — страница Prompts («SEO Workflow Optimizer») и API": "2026-03-prompts-page-seo-workflow-optimizer.md",
    "Март–апрель 2026 — обновления (стабильность `html_structure`, промпты, UI)": "2026-03-04-html-structure-stability-prompts-ui.md",
    "Март 2026 — Sites, Blueprints, Projects (формы и API)": "2026-03-sites-blueprints-projects-forms-api.md",
    "30 марта 2026 — Projects: `POST` body, `GET` progress, Axios toast, Error Boundary": "2026-03-30-projects-post-body-axios-toast.md",
    "30 марта 2026 — Проекты: архивация, устойчивость к сбоям SERP, расширение API и UI": "2026-03-30-projects-archive-serp-resilience.md",
    "Март 2026 — Проекты: preview (dry-run), SERP-конфиг, CSV, health-check SERP": "2026-03-projects-preview-serp-config-csv.md",
    "Март 2026 — Задачи (Tasks), деталь задачи, шаги pipeline (StepCard)": "2026-03-tasks-detail-step-card.md",
    "Март 2026 — Image pipeline (актуализация)": "2026-03-image-pipeline-update.md",
    "Март 2026 — SERP/Scraping cache (актуализация)": "2026-03-serp-scraping-cache-update.md",
    "28 марта 2026 — статьи: `meta_data`, контроль слов по шагам": "2026-03-28-articles-meta-data-word-count.md",
    "28 марта 2026 — парсер MULTIMEDIA для image pipeline (`image_utils.py`)": "2026-03-28-multimedia-parser-image-pipeline.md",
    "28 марта 2026 — `max_tokens` в LLM (OpenRouter)": "2026-03-28-max-tokens-llm-openrouter.md",
}

LEGACY_FOCUS_FILE = "2026-03-v2-legacy-sprint-and-hotfixes.md"


def slug_fallback(title: str) -> str:
    """ASCII slug if mapping missing."""
    t = title.lower()
    t = re.sub(r"[^a-z0-9а-яё]+", "-", t, flags=re.I)
    t = re.sub(r"-+", "-", t).strip("-")
    # crude transliteration for cyrillic chunk
    tr = str.maketrans(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        "abvgdeejzijklmnoprstufhccss-y-e-ju-a",
    )
    t = t.translate(tr)
    t = re.sub(r"[^a-z0-9-]+", "-", t)
    return (t[:80] or "entry").rstrip("-") + ".md"


def guess_date(title: str) -> str:
    m = re.search(r"(\d{1,2})\s+(январ|феврал|март|апрел|ма|июн|июл|август|сентябр|октябр|ноябр|декабр)", title, re.I)
    months = {
        "январ": "01",
        "феврал": "02",
        "март": "03",
        "апрел": "04",
        "ма": "05",
        "июн": "06",
        "июл": "07",
        "август": "08",
        "сентябр": "09",
        "октябр": "10",
        "ноябр": "11",
        "декабр": "12",
    }
    if m:
        day = int(m.group(1))
        mo = months.get(m.group(2).lower()[:5], "01")
        return f"2026-{mo}-{day:02d}"
    if "Май 2026" in title:
        return "2026-05-01"
    if "Апрель 2026" in title:
        return "2026-04-01"
    if "Март 2026" in title or title.startswith("Март"):
        return "2026-03-01"
    return "2026-01-01"


def parse_sections(text: str) -> list[tuple[str, str, int]]:
    """Return list of (title, body, start_line_1based)."""
    lines = text.splitlines()
    out: list[tuple[str, str, int]] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("### "):
            title = lines[i][4:].strip()
            title_line_1based = i + 1
            i += 1
            body_lines: list[str] = []
            while i < len(lines):
                if lines[i].startswith("### ") or lines[i].startswith("## "):
                    break
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines).strip()
            out.append((title, body, title_line_1based))
        else:
            i += 1
    return out


def teaser_from_body(body: str, title: str) -> str:
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith("---"):
            continue
        # Prefer first bold one-liner context line
        if s.startswith("**") and len(s) < 240:
            return s.replace("**", "")[:220] + ("…" if len(s) > 220 else "")
        if len(s) > 40:
            return s[:200] + ("…" if len(s) > 200 else "")
    return title[:160]


def write_changelog(title: str, body: str, filename: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    date = guess_date(title)
    content = (
        f"# {title}\n\n"
        f"**Дата:** {date}\n"
        f"**Контекст:** см. также docs/CURRENT_STATUS.md, docs/PROJECT_OVERVIEW.md\n\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    sections = parse_sections(text)

    written: list[tuple[str, str, str]] = []  # title, filename, month_key for index

    for title, body, _ln in sections:
        if title in KEEP_FULL_TITLES:
            continue
        if title in INVENTORY_TITLES:
            continue
        fn = TITLE_TO_FILE.get(title)
        if not fn:
            fn = slug_fallback(title)
        write_changelog(title, body, fn)
        mk = fn[:7] if fn[0].isdigit() else fn.split("-")[0]
        written.append((title, fn, mk))

    # Legacy block under «Текущий фокус» (non-### paragraphs)
    legacy_start = text.index("**Что было сделано в последнем спринте")
    legacy_end = text.index("**Что происходит сейчас:**")
    tail = text.index("- Формируется backlog", legacy_start)
    legacy_body = text[legacy_start : tail + 80].strip()
    # trim trailing separator line after последний bullet block
    legacy_body = legacy_body.split("---")[0].strip()
    write_changelog(
        "v2.0: исторический спринт React и hotfixes (архив)",
        legacy_body,
        LEGACY_FOCUS_FILE,
    )
    written.append(("v2.0: исторический спринт React и hotfixes (архив)", LEGACY_FOCUS_FILE, "2026-03"))

    # README index (group by YYYY-MM from filename)
    by_month: dict[str, list[tuple[str, str]]] = {}
    for title, fn, _ in written:
        key = fn[:7] if re.match(r"^\d{4}-\d{2}", fn) else "other"
        by_month.setdefault(key, []).append((title, fn))

    lines = [
        "# Changelog index",
        "",
        "Полные тексты датированных записей из `docs/CURRENT_STATUS.md` (разнесены для навигации). Новые записи добавляйте отдельным файлом здесь и коротким тизером в `CURRENT_STATUS.md`.",
        "",
    ]
    for month in sorted(by_month.keys(), reverse=True):
        lines.append(f"## {month}")
        lines.append("")
        for title, fn in sorted(by_month[month], key=lambda x: x[1]):
            one = title.replace("\n", " ")
            if len(one) > 120:
                one = one[:117] + "…"
            lines.append(f"- [{one}]({fn})")
        lines.append("")

    (OUT_DIR / "README.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"Wrote {len(written)} changelog files under {OUT_DIR}")
    build_slim_current_status(text, sections)


def teaser_block(title: str, body: str) -> str:
    fn = TITLE_TO_FILE.get(title) or slug_fallback(title)
    fn = fn.rstrip("/")
    t = teaser_from_body(body, title)
    return (
        f"### {title}\n\n"
        f"{t}\n\n"
        f"**Полный текст:** [changelog/{fn}](changelog/{fn}).\n\n"
        f"---\n"
    )


def build_slim_current_status(raw: str, sections: list[tuple[str, str, int]]) -> None:
    """Rewrite docs/CURRENT_STATUS.md to slim form + teasers."""
    lines = raw.splitlines()
    focus_heading = "## 🚧 Текущий фокус (v2.0 MVP завершён)"
    backlog_heading = "## 📋 Следующие задачи"
    idx_focus = next(i for i, ln in enumerate(lines) if ln == focus_heading)
    idx_backlog = next(i for i, ln in enumerate(lines) if ln == backlog_heading)
    idx_done = next(i for i, ln in enumerate(lines) if ln.startswith("## ✅ Выполнено"))
    line_done_1based = idx_done + 1
    line_focus_1based = idx_focus + 1
    line_backlog_1based = idx_backlog + 1

    title_to_body = {t: b for t, b, _ in sections}

    out: list[str] = []
    out.append("# ТЕКУЩИЙ СТАТУС ПРОЕКТА")
    out.append("")
    out.append(
        "**Дата последнего обновления:** май 2026 — длинный changelog вынесен в "
        "**`docs/changelog/`** ([индекс](changelog/README.md)). Ниже сохранены те же заголовки "
        "**`### …`** (якоря для ссылок из других документов): последние записи — полным текстом, "
        "остальные — краткий тизер и ссылка на файл."
    )
    out.append("")
    out.append("---")
    out.append("")

    for title, body, ln in sections:
        if ln >= line_done_1based:
            break
        if title in INVENTORY_TITLES:
            continue
        if title in KEEP_FULL_TITLES:
            b = body.rstrip()
            if b.endswith("---"):
                b = b[: b.rfind("---")].rstrip()
            out.append(f"### {title}")
            out.append("")
            out.append(b)
            out.append("")
            out.append("---")
            out.append("")
        elif title == "31 марта 2026 — Pipeline Observability + Isolated Project Pages":
            continue
        else:
            out.append(teaser_block(title, body).rstrip())
            out.append("")

    # ## ✅ Выполнено block: copy raw from original, swap Pipeline Observability body for teaser
    done_chunk = "\n".join(lines[idx_done:idx_focus]).strip()
    obs_title = "31 марта 2026 — Pipeline Observability + Isolated Project Pages"
    obs_fn = TITLE_TO_FILE[obs_title]
    obs_body = title_to_body[obs_title]
    replacement = (
        f"### {obs_title}\n\n"
        f"{teaser_from_body(obs_body, obs_title)}\n\n"
        f"**Полный текст:** [changelog/{obs_fn}](changelog/{obs_fn}).\n"
    )
    marker = f"### {obs_title}\n\n"
    next_admin = "\n### Админ-панель (React SPA)"
    if marker in done_chunk and next_admin in done_chunk:
        i0 = done_chunk.index(marker)
        i1 = done_chunk.index(next_admin, i0)
        done_chunk = done_chunk[:i0] + replacement + done_chunk[i1:]
    else:
        import sys

        print("WARNING: could not splice Pipeline Observability section in Выполнено", file=sys.stderr)
    dc = done_chunk.rstrip()
    out.append(dc)
    out.append("")
    if not dc.endswith("---"):
        out.append("---")
        out.append("")

    # Focus: short intro + teaser-only subsections + legacy
    out.append(focus_heading)
    out.append("")
    out.append(
        "**Статус:** React SPA (v2.0) в продакшене. Текущий инженерный фокус Q2 2026 — "
        "**Quality Gate**, расширение **fallback** моделей и устойчивость long-running задач; "
        "сводный бэклог — [Roadmap.md](Roadmap.md#текущий-бэклог). "
        "Ниже — архивные заметки по эволюции Prompts / Projects / Tasks (март–апрель 2026) "
        "в формате тизер + полный текст в `changelog/`."
    )
    out.append("")
    for title, body, ln in sections:
        if ln <= line_focus_1based:
            continue
        if ln >= line_backlog_1based:
            break
        out.append(teaser_block(title, body).rstrip())
        out.append("")

    leg_fn = LEGACY_FOCUS_FILE
    out.append("### v2.0: исторический спринт React и hotfixes (архив)")
    out.append("")
    out.append(
        "Сводка завершённого спринта миграции UI и списка hotfixes по Prompts/Tasks/Articles — "
        f"перенесена в [changelog/{leg_fn}](changelog/{leg_fn})."
    )
    out.append("")
    out.append("---")
    out.append("")

    out.append("## 📋 Следующие задачи")
    out.append("")
    out.append("См. [Roadmap.md](Roadmap.md#текущий-бэклог).")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## 🐛 Известные проблемы")
    out.append("")
    out.append("См. [Bugs.md](Bugs.md#известные-ограничения).")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## 💡 Идеи для улучшения")
    out.append("")
    out.append("См. [Roadmap.md](Roadmap.md#идеи).")
    out.append("")

    SRC.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
