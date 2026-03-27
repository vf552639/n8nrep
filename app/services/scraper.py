import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from urllib.parse import urlparse
import time
import concurrent.futures

def parse_html(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract headers
    headers = {f"h{i}": [] for i in range(1, 7)}
    for i in range(1, 7):
        tags = soup.find_all(f"h{i}")
        headers[f"h{i}"] = [tag.get_text(strip=True) for tag in tags if tag.get_text(strip=True)]
        
    # Extract body text
    # Remove script, style, header, footer, nav
    for element in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
        element.decompose()
        
    text = soup.get_text(separator=' ', strip=True)
    word_count = len(text.split())
    
    return {
        "headers": headers,
        "text": text,
        "word_count": word_count
    }
from app.config import settings
from app.services.notifier import notify_serper_key_issue
from app.services.serp import _is_excluded_domain
from app.services.serp_cache import get_cached_scrape_item, set_cached_scrape_item

_serper_key_failed = False

def scrape_via_serper(url: str, timeout: int = 30) -> str:
    global _serper_key_failed
    try:
        response = requests.post(
            "https://scrape.serper.dev/",
            headers={
                "X-API-KEY": settings.SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={"url": url, "includeHtml": True},
            timeout=timeout
        )
        
        if response.status_code in [401, 403]:
            if not _serper_key_failed:
                _serper_key_failed = True
                notify_serper_key_issue(f"HTTP {response.status_code} - Unauthorized or Forbidden.")
            return None
            
        try:
            data = response.json()
        except:
            return None
            
        if "message" in data:
            msg = str(data["message"]).lower()
            if any(err in msg for err in ["invalid api key", "quota exceeded", "rate limit"]):
                if not _serper_key_failed:
                    _serper_key_failed = True
                    notify_serper_key_issue(data["message"])
                return None
                
        return data.get("html")
    except Exception as e:
        return None

def scrape_urls(urls: List[str], max_urls: int = 10, timeout: int = 15) -> Dict[str, Any]:
    """
    Scrapes a list of urls and returns combined results for the LLM analysis.
    """
    global _serper_key_failed
    _serper_key_failed = False
    
    results = []
    failed_results = []
    urls_to_scrape = [url for url in urls if not _is_excluded_domain(url)][:max_urls]
    cache_hits = 0
    cache_misses = 0
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    def scrape_single(url: str):
        domain = urlparse(url).netloc
        
        # Step 1: Serper.dev
        if getattr(settings, "SERPER_API_KEY", None) and not _serper_key_failed:
            html = scrape_via_serper(url)
            if html:
                try:
                    parsed_data = parse_html(html)
                    return (True, {
                        "url": url,
                        "domain": domain,
                        "headers": parsed_data["headers"],
                        "text": parsed_data["text"],
                        "word_count": parsed_data["word_count"],
                        "method": "serper"
                    })
                except Exception as e:
                    pass # Fall back to direct
        
        # Step 2: Direct Request (Fallback)
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                parsed_data = parse_html(response.text)
                return (True, {
                    "url": url,
                    "domain": domain,
                    "headers": parsed_data["headers"],
                    "text": parsed_data["text"],
                    "word_count": parsed_data["word_count"],
                    "method": "direct"
                })
            else:
                return (False, {
                    "url": url,
                    "domain": domain,
                    "error": f"HTTP {response.status_code}"
                })
        except requests.exceptions.Timeout:
            return (False, {
                "url": url,
                "domain": domain,
                "error": f"Timeout after {timeout}s"
            })
        except requests.exceptions.ConnectionError:
            return (False, {
                "url": url,
                "domain": domain,
                "error": "Connection error"
            })
        except Exception as e:
            return (False, {
                "url": url,
                "domain": domain,
                "error": str(e)
            })

    # Try cache first, scrape only misses
    urls_missed_cache = []
    for url in urls_to_scrape:
        cached = get_cached_scrape_item(url)
        if cached and isinstance(cached, dict):
            cache_hits += 1
            parsed_headers = cached.get("headers", {})
            parsed_text = cached.get("text", "")
            parsed_word_count = cached.get("word_count", 0)
            results.append({
                "url": url,
                "domain": cached.get("domain") or urlparse(url).netloc,
                "headers": parsed_headers if isinstance(parsed_headers, dict) else {},
                "text": str(parsed_text),
                "word_count": int(parsed_word_count or 0),
                "method": "cache",
            })
        else:
            cache_misses += 1
            urls_missed_cache.append(url)

    # Use ThreadPoolExecutor to scrape in parallel
    if urls_missed_cache:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(urls_missed_cache))) as executor:
            future_to_url = {executor.submit(scrape_single, url): url for url in urls_missed_cache}
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    success, data = future.result()
                    if success:
                        results.append(data)
                        set_cached_scrape_item(
                            data["url"],
                            {
                                "text": data.get("text", ""),
                                "word_count": data.get("word_count", 0),
                                "headers": data.get("headers", {}),
                                "domain": data.get("domain", ""),
                            },
                        )
                    else:
                        failed_results.append(data)
                        print(f"Failed scraping {data['url']}: {data['error']}")
                except Exception as exc:
                    url = future_to_url[future]
                    domain = urlparse(url).netloc
                    failed_results.append({"url": url, "domain": domain, "error": f"Execution exception: {exc}"})
                    print(f"{url} generated an execution exception: {exc}")
        
    if len(results) < 3:
        print(f"Warning: Only {len(results)} successful scrapes (minimum recommended: 3)")
        if len(results) == 0:
            raise Exception(f"All competitors failed to scrape (0 successful out of {len(urls_to_scrape)}). Check failed_results: {failed_results}")
        
    # Aggregate data
    all_h1_h6 = []
    merged_text = ""
    total_words = 0
    
    for r in results:
        merged_text += f"\n\n--- Source: {r['domain']} ---\n{r['text']}"
        total_words += r['word_count']
        all_h1_h6.append({
            "domain": r['domain'],
            "headers": r['headers']
        })
        
    avg_words = total_words // len(results) if len(results) > 0 else 0
        
    return {
        "successful_scrapes": len(results),
        "total_attempted": len(urls_to_scrape),
        "average_word_count": avg_words,
        "merged_text": merged_text,
        "headers_structure": all_h1_h6,
        "raw_results": results,
        "failed_results": failed_results,
        "serper_count": len([r for r in results if r.get("method") == "serper"]),
        "direct_count": len([r for r in results if r.get("method") == "direct"]),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
    }
