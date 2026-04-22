import json

from app.models.project import SiteProject
from app.services.pipeline.errors import LLMError, ScrapingError, SerpError
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline_constants import STEP_SCRAPING, STEP_SERP
from app.services.scraper import scrape_urls
from app.services.serp import fetch_serp_data
from app.services.url_utils import merge_urls_dedup_by_domain, normalize_url


def _safe_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return [item for item in val if item is not None]
    return []


class SerpStep:
    name = STEP_SERP
    policy = StepPolicy(retryable_errors=(SerpError, LLMError), max_retries=1)

    def run(self, ctx) -> StepResult:
        if ctx.task.serp_data:
            return StepResult(status="completed", result=json.dumps({"skipped": True}))

        add_log(ctx.db, ctx.task, "Fetching SERP data...", step=STEP_SERP)
        try:
            serp_data = fetch_serp_data(
                ctx.task.main_keyword,
                ctx.task.country,
                ctx.task.language,
                serp_config=ctx.task.serp_config,
            )
        except Exception as serp_err:
            add_log(
                ctx.db,
                ctx.task,
                f"❌ SERP fetch failed: {serp_err!s}",
                level="error",
                step=STEP_SERP,
            )
            raise SerpError(str(serp_err)) from serp_err

        user_urls: list[str] = []
        if ctx.task.project_id:
            project_row = ctx.db.query(SiteProject).filter(SiteProject.id == ctx.task.project_id).first()
            if project_row and project_row.competitor_urls:
                user_urls = [u for u in (normalize_url(x) for x in project_row.competitor_urls) if u]

        if user_urls and isinstance(serp_data, dict):
            orig_urls = list(serp_data.get("urls") or [])
            merged, duplicates = merge_urls_dedup_by_domain(orig_urls, user_urls)
            serp_data["urls"] = merged
            serp_data["user_competitor_urls"] = user_urls
            serp_data["user_competitor_duplicates"] = duplicates
            add_log(
                ctx.db,
                ctx.task,
                f"Merged {len(user_urls)} user URLs ({len(duplicates)} duplicate domains skipped); "
                f"SERP urls: {len(orig_urls)} → {len(merged)}",
                step=STEP_SERP,
            )

        ctx.task.serp_data = serp_data
        ctx.db.commit()
        add_log(ctx.db, ctx.task, "SERP Research completed.", step=STEP_SERP)

        def _safe_len(val) -> int:
            return len(val) if isinstance(val, list) else 0

        serp_summary = {
            "source": serp_data.get("source", "unknown") if isinstance(serp_data, dict) else "unknown",
            "_from_cache": bool(serp_data.get("_from_cache")) if isinstance(serp_data, dict) else False,
            "urls_count": _safe_len(serp_data.get("urls")) if isinstance(serp_data, dict) else 0,
            "organic_count": _safe_len(serp_data.get("organic_results"))
            if isinstance(serp_data, dict)
            else 0,
            "paa_count": _safe_len(serp_data.get("paa_full")) if isinstance(serp_data, dict) else 0,
            "related_count": _safe_len(serp_data.get("related_searches"))
            if isinstance(serp_data, dict)
            else 0,
            "has_featured_snippet": serp_data.get("featured_snippet") is not None
            if isinstance(serp_data, dict)
            else False,
            "has_knowledge_graph": serp_data.get("knowledge_graph") is not None
            if isinstance(serp_data, dict)
            else False,
            "has_ai_overview": serp_data.get("ai_overview") is not None
            if isinstance(serp_data, dict)
            else False,
            "has_answer_box": serp_data.get("answer_box") is not None
            if isinstance(serp_data, dict)
            else False,
            "ads_count": serp_data.get("search_intent_signals", {}).get("ads_count", 0)
            if isinstance(serp_data, dict)
            else 0,
            "people_also_search_count": _safe_len(serp_data.get("people_also_search"))
            if isinstance(serp_data, dict)
            else 0,
            "people_also_search": _safe_list(serp_data.get("people_also_search"))
            if isinstance(serp_data, dict)
            else [],
            "serp_features": _safe_list(serp_data.get("serp_features"))
            if isinstance(serp_data, dict)
            else [],
            "urls": _safe_list(serp_data.get("urls")) if isinstance(serp_data, dict) else [],
            "user_competitor_urls_count": len(user_urls) if isinstance(serp_data, dict) else 0,
            "user_competitor_duplicates": list(serp_data.get("user_competitor_duplicates") or [])
            if isinstance(serp_data, dict)
            else [],
        }
        if isinstance(serp_data, dict) and serp_data.get("source") == "google+bing":
            serp_summary["google_data"] = serp_data.get("google_data")
            serp_summary["bing_data"] = serp_data.get("bing_data")

        if not ctx.auto_mode:
            step_results = dict(ctx.task.step_results or {})
            step_results["_pipeline_pause"] = {"active": True, "reason": "serp_review"}
            ctx.task.step_results = step_results
            ctx.task.status = "paused"
            ctx.db.commit()
            add_log(
                ctx.db,
                ctx.task,
                "⏸️ Pipeline paused: waiting for SERP URLs review",
                step=STEP_SERP,
            )

        return StepResult(status="completed", result=json.dumps(serp_summary, ensure_ascii=False))


class ScrapingStep:
    name = STEP_SCRAPING
    policy = StepPolicy(retryable_errors=(ScrapingError,), max_retries=1)

    def run(self, ctx) -> StepResult:
        if ctx.task.competitors_text:
            return StepResult(status="completed", result=json.dumps({"skipped": True}))

        serp_data = ctx.task.serp_data if isinstance(ctx.task.serp_data, dict) else {}
        urls = serp_data.get("urls", [])
        if not urls:
            serp_source = serp_data.get("source", "unknown")
            add_log(
                ctx.db,
                ctx.task,
                f"❌ No organic URLs in SERP data (source={serp_source}) — pipeline stopped. "
                "Check SERP step logs for debug info.",
                level="error",
                step=STEP_SCRAPING,
            )
            raise ScrapingError(
                f"Pipeline stopped: SERP returned 0 organic URLs (source={serp_source}). Cannot proceed without competitor data."
            )

        add_log(ctx.db, ctx.task, f"Scraping {len(urls)} competitors...", step=STEP_SCRAPING)

        scrape_data = scrape_urls(urls)
        ctx.task.competitors_text = scrape_data["merged_text"]
        ctx.task.outline = {
            "scrape_info": {
                "avg_words": scrape_data["average_word_count"],
                "headers": scrape_data["headers_structure"],
            }
        }
        ctx.db.commit()
        ctx.outline_data = ctx.task.outline

        scrape_summary = {
            "total_from_serp": len(urls),
            "total_attempted": scrape_data["total_attempted"],
            "successful": scrape_data["successful_scrapes"],
            "failed": scrape_data["total_attempted"] - scrape_data["successful_scrapes"],
            "avg_word_count": scrape_data["average_word_count"],
            "scraped_domains": [r["domain"] for r in scrape_data["raw_results"]],
            "scraped_urls": [r["url"] for r in scrape_data["raw_results"]],
            "scraped_titles": scrape_data.get("scraped_titles", []),
            "scraped_descriptions": scrape_data.get("scraped_descriptions", []),
            "titles_source": "scraping",
            "descriptions_source": "scraping",
            "failed_results": scrape_data.get("failed_results", []),
            "serper_count": scrape_data.get("serper_count", 0),
            "direct_count": scrape_data.get("direct_count", 0),
            "cache_hits": scrape_data.get("cache_hits", 0),
            "cache_misses": scrape_data.get("cache_misses", 0),
        }

        add_log(
            ctx.db,
            ctx.task,
            f"Scraped competitors. Avg word count: {scrape_data['average_word_count']}",
            step=STEP_SCRAPING,
        )
        return StepResult(status="completed", result=json.dumps(scrape_summary, ensure_ascii=False))


register_step(SerpStep())
register_step(ScrapingStep())
