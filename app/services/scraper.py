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

def scrape_urls(urls: List[str], max_urls: int = 10, timeout: int = 15) -> Dict[str, Any]:
    """
    Scrapes a list of urls and returns combined results for the LLM analysis.
    """
    results = []
    urls_to_scrape = urls[:max_urls]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    def scrape_single(url: str):
        try:
            domain = urlparse(url).netloc
            response = requests.get(url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                parsed_data = parse_html(response.text)
                return {
                    "url": url,
                    "domain": domain,
                    "headers": parsed_data["headers"],
                    "text": parsed_data["text"],
                    "word_count": parsed_data["word_count"]
                }
            else:
                print(f"Skipping {url}: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    # Use ThreadPoolExecutor to scrape in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(urls_to_scrape))) as executor:
        future_to_url = {executor.submit(scrape_single, url): url for url in urls_to_scrape}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as exc:
                url = future_to_url[future]
                print(f"{url} generated an exception: {exc}")
        
    if len(results) < 3:
        print(f"Warning: Only {len(results)} successful scrapes (minimum recommended: 3)")
        if len(results) == 0:
            raise Exception("All competitors failed to scrape (0 successful).")
        
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
        "raw_results": results
    }
