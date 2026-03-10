import requests
import json
import base64
from typing import Dict, Any, Optional
from app.config import settings

def _get_dataforseo_auth_header() -> str:
    login = settings.DATAFORSEO_LOGIN
    password = settings.DATAFORSEO_PASSWORD
    credentials = f"{login}:{password}"
    return "Basic " + base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

def _map_location_dataforseo(location: str) -> int:
    loc = location.lower().strip()
    mapping = {
        "us": 2840, "usa": 2840, "united states": 2840,
        "uk": 2826, "gb": 2826, "united kingdom": 2826,
        "de": 2276, "germany": 2276,
        "pl": 2616, "poland": 2616,
        "fr": 2250, "france": 2250,
        "it": 2380, "italy": 2380,
        "es": 2724, "spain": 2724,
        "ru": 2643, "russia": 2643,
        "ua": 2804, "ukraine": 2804,
        "ca": 2124, "canada": 2124,
        "au": 2036, "australia": 2036,
        "br": 2076, "brazil": 2076,
        "in": 2356, "india": 2356,
        "nl": 2528, "netherlands": 2528,
    }
    return mapping.get(loc, 2840) # Default to US

def _map_language_dataforseo(lang: str) -> str:
    lang = lang.lower().strip()
    mapping = {
        "en": "en", "english": "en",
        "de": "de", "german": "de",
        "pl": "pl", "polish": "pl",
        "fr": "fr", "french": "fr",
        "it": "it", "italian": "it",
        "es": "es", "spanish": "es",
        "ru": "ru", "russian": "ru",
        "uk": "uk", "ukrainian": "uk",
    }
    return mapping.get(lang, "en") # Default to english

def call_dataforseo(keyword: str, location_code: str, language_code: str) -> Optional[Dict[str, Any]]:
    url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
    headers = {
        'Authorization': _get_dataforseo_auth_header(),
        'Content-Type': 'application/json'
    }
    
    dfs_loc = _map_location_dataforseo(location_code)
    dfs_lang = _map_language_dataforseo(language_code)
    
    payload = [{
        "keyword": keyword,
        "location_code": dfs_loc,
        "language_code": dfs_lang,
        "depth": 10
    }]
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, dict) and data.get("tasks") and len(data["tasks"]) > 0:
            task_result = data["tasks"][0].get("result", [])
            if task_result and len(task_result) > 0:
                return task_result[0]
        return None
    except Exception as e:
        print(f"DataForSEO error: {e}")
        return None

def _map_location_serpapi(location: str) -> str:
    loc = location.lower().strip()
    mapping = {
        "us": "United States", "usa": "United States",
        "uk": "United Kingdom", "gb": "United Kingdom",
        "de": "Germany",
        "pl": "Poland",
        "fr": "France",
        "it": "Italy",
        "es": "Spain",
        "ru": "Russia",
        "ua": "Ukraine",
        "ca": "Canada",
        "au": "Australia",
        "br": "Brazil",
        "in": "India",
        "nl": "Netherlands"
    }
    return mapping.get(loc, location.title()) # Default to capitalized string

def _map_language_serpapi(lang: str) -> str:
    lang = lang.lower().strip()
    mapping = {
        "en": "en", "english": "en",
        "de": "de", "german": "de",
        "pl": "pl", "polish": "pl",
        "fr": "fr", "french": "fr",
        "it": "it", "italian": "it",
        "es": "es", "spanish": "es",
        "ru": "ru", "russian": "ru",
        "uk": "uk", "ukrainian": "uk",
    }
    return mapping.get(lang, lang.lower())

def call_serpapi(keyword: str, location: str, language: str) -> Optional[Dict[str, Any]]:
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": keyword,
        "gl": _map_location_serpapi(location) if len(location) == 2 else location, # gl mostly expects 2-letter country code
        "hl": _map_language_serpapi(language),
        "num": 10,
        "api_key": settings.SERPAPI_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"SerpAPI HTTP error: {e} - Response: {e.response.text if e.response else 'Unknown'}")
        return None
    except Exception as e:
        print(f"SerpAPI error: {e}")
        return None

def _empty_serp_result() -> Dict[str, Any]:
    return {
        "source": "none",
        "urls": [],
        "organic_results": [],
        "paa": [],
        "paa_full": [],
        "related_searches": [],
        "related_searches_full": [],
        "featured_snippet": None,
        "knowledge_graph": None,
        "ai_overview": None,
        "answer_box": None,
        "serp_features": [],
        "total_results": 0,
        "search_intent_signals": {},
        "raw_response": None
    }

def _detect_snippet_type(item: dict) -> str:
    if item.get("table"):
        return "table"
    desc = item.get("description", "")
    if desc.startswith(("1.", "•", "-", "Step")):
        return "list"
    return "paragraph"

def _parse_organic(item: dict, result: dict):
    url = item.get("url")
    if not url:
        return
    result["urls"].append(url)
    result["organic_results"].append({
        "url": url,
        "domain": item.get("domain", ""),
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "breadcrumb": item.get("breadcrumb", ""),
        "rank_group": item.get("rank_group", 0),
        "rank_absolute": item.get("rank_absolute", 0),
        "is_featured_snippet": item.get("is_featured_snippet", False),
        "highlighted": item.get("highlighted") or [],
        "pre_snippet": item.get("pre_snippet"),
        "extended_snippet": item.get("extended_snippet"),
    })

def _parse_featured_snippet(item: dict, result: dict):
    result["featured_snippet"] = {
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "featured_title": item.get("featured_title", ""),
        "url": item.get("url", ""),
        "domain": item.get("domain", ""),
        "type": _detect_snippet_type(item),
    }

def _parse_paa(item: dict, result: dict):
    for paa_item in (item.get("items") or []):
        if isinstance(paa_item, dict):
            question = paa_item.get("title") or paa_item.get("question") or ""
            if question:
                result["paa"].append(question)  # backward compat
                result["paa_full"].append({
                    "question": question,
                    "answer": paa_item.get("description", ""),
                    "url": paa_item.get("url", ""),
                    "domain": paa_item.get("domain", ""),
                })
        elif isinstance(paa_item, str) and paa_item.strip():
            result["paa"].append(paa_item.strip())

def _parse_related_searches(item: dict, result: dict):
    for rs_item in (item.get("items") or []):
        if isinstance(rs_item, dict):
            query = rs_item.get("title") or rs_item.get("query") or ""
            if query:
                result["related_searches"].append(query)  # backward compat
                result["related_searches_full"].append({
                    "query": query,
                    "highlighted": rs_item.get("highlighted", []),
                })
        elif isinstance(rs_item, str) and rs_item.strip():
            result["related_searches"].append(rs_item.strip())

def _parse_knowledge_graph(item: dict, result: dict):
    facts = []
    for kg_item in (item.get("items") or []):
        if kg_item.get("type") == "knowledge_graph_row_item":
            facts.append({
                "label": kg_item.get("title", ""),
                "value": kg_item.get("text", "") or kg_item.get("description", "")
            })
    result["knowledge_graph"] = {
        "title": item.get("title", ""),
        "subtitle": item.get("subtitle", ""),
        "description": item.get("description", ""),
        "facts": facts,
    }

def _parse_ai_overview(item: dict, result: dict):
    texts = []
    references = []
    for ao_item in (item.get("items") or []):
        if ao_item.get("text"):
            texts.append(ao_item["text"])
        for ref in (ao_item.get("references") or []):
            references.append({
                "url": ref.get("url", ""),
                "domain": ref.get("domain", ""),
                "title": ref.get("title", ""),
            })
    if texts or references:
        result["ai_overview"] = {
            "text": "\n".join(texts),
            "references": references,
        }

def _parse_answer_box(item: dict, result: dict):
    text = item.get("description", "") or item.get("text", "")
    if text:
        result["answer_box"] = {
            "type": item.get("type", "answer_box"),
            "text": text,
            "url": item.get("url"),
        }

def _parse_dataforseo_response(dfs_data: dict) -> dict:
    """
    Парсит полный ответ DataForSEO в обогащённую структуру.
    Сохраняет backward compatibility через дублирование 
    (urls, paa, related_searches остаются как раньше).
    """
    result = _empty_serp_result()
    result["source"] = "dataforseo"
    result["raw_response"] = dfs_data
    result["total_results"] = dfs_data.get("se_results_count", 0)
    
    serp_features_set = set()
    ads_count = 0
    
    for item in dfs_data.get("items", []):
        item_type = item.get("type", "")
        if item_type:
            serp_features_set.add(item_type)
        
        if item_type == "organic":
            _parse_organic(item, result)
        elif item_type == "featured_snippet":
            _parse_featured_snippet(item, result)
        elif item_type == "people_also_ask":
            _parse_paa(item, result)
        elif item_type == "related_searches":
            _parse_related_searches(item, result)
        elif item_type == "knowledge_graph":
            _parse_knowledge_graph(item, result)
        elif item_type == "ai_overview":
            _parse_ai_overview(item, result)
        elif item_type == "answer_box":
            _parse_answer_box(item, result)
        elif item_type in ("paid", "shopping"):
            ads_count += 1
            
    result["serp_features"] = sorted(list(serp_features_set))
    result["search_intent_signals"] = {
        "has_featured_snippet": result["featured_snippet"] is not None,
        "has_knowledge_graph": result["knowledge_graph"] is not None,
        "has_local_pack": "local_pack" in serp_features_set,
        "has_shopping": "shopping" in serp_features_set,
        "has_video": "video" in serp_features_set,
        "has_ai_overview": result["ai_overview"] is not None,
        "organic_count": len(result["organic_results"]),
        "ads_count": ads_count
    }
    
    return result

def _parse_serpapi_response(serp_data: dict) -> dict:
    result = _empty_serp_result()
    result["source"] = "serpapi"
    result["raw_response"] = serp_data
    result["total_results"] = serp_data.get("search_information", {}).get("total_results", 0)
    
    serp_features_set = set()
    ads_count = 0
    
    # Organic results
    for item in serp_data.get("organic_results", []):
        serp_features_set.add("organic")
        url = item.get("link")
        if url:
            result["urls"].append(url)
            result["organic_results"].append({
                "url": url,
                "domain": item.get("displayed_link", ""),
                "title": item.get("title", ""),
                "description": item.get("snippet", ""),
                "breadcrumb": "",
                "rank_group": item.get("position", 0),
                "rank_absolute": item.get("position", 0),
                "is_featured_snippet": False,
                "highlighted": item.get("snippet_highlighted_words") or [],
                "pre_snippet": None,
                "extended_snippet": None,
            })
            
    # Related Questions (PAA)
    if "related_questions" in serp_data:
        serp_features_set.add("people_also_ask")
        for q in serp_data["related_questions"]:
            question = q.get("question", "")
            if question:
                result["paa"].append(question)
                result["paa_full"].append({
                    "question": question,
                    "answer": q.get("snippet", ""),
                    "url": q.get("link", ""),
                    "domain": q.get("displayed_link", ""),
                })
                
    # Related Searches
    if "related_searches" in serp_data:
        serp_features_set.add("related_searches")
        for rs in serp_data["related_searches"]:
            query = rs.get("query", "")
            if query:
                result["related_searches"].append(query)
                result["related_searches_full"].append({
                    "query": query,
                    "highlighted": [],
                })
                
    # Answer Box / Featured Snippet
    if "answer_box" in serp_data:
        ans = serp_data["answer_box"]
        if ans.get("type") in ("organic_result", "featured_snippet"):
            serp_features_set.add("featured_snippet")
            result["featured_snippet"] = {
                "title": ans.get("title", ""),
                "description": ans.get("snippet", "") or ans.get("answer", ""),
                "featured_title": "",
                "url": ans.get("link", ""),
                "domain": ans.get("displayed_link", ""),
                "type": "paragraph" if not ans.get("list") else "list",
            }
        else:
            serp_features_set.add("answer_box")
            text = ans.get("answer", "") or ans.get("snippet", "")
            if text:
                result["answer_box"] = {
                    "type": ans.get("type", "answer_box"),
                    "text": text,
                    "url": ans.get("link"),
                }
                
    # Knowledge Graph
    if "knowledge_graph" in serp_data:
        serp_features_set.add("knowledge_graph")
        kg = serp_data["knowledge_graph"]
        facts = []
        for key, value in kg.items():
            if isinstance(value, str) and key not in ("title", "type", "description", "header_images", "image"):
                facts.append({"label": key.replace("_", " ").title(), "value": value})
        
        result["knowledge_graph"] = {
            "title": kg.get("title", ""),
            "subtitle": kg.get("type", ""),
            "description": kg.get("description", ""),
            "facts": facts,
        }
        
    ads_count = len(serp_data.get("ads", []))
    if ads_count > 0:
        serp_features_set.add("paid")
        
    result["serp_features"] = sorted(list(serp_features_set))
    result["search_intent_signals"] = {
        "has_featured_snippet": result["featured_snippet"] is not None,
        "has_knowledge_graph": result["knowledge_graph"] is not None,
        "has_local_pack": "local_results" in serp_data,
        "has_shopping": "shopping_results" in serp_data,
        "has_video": "video_results" in serp_data,
        "has_ai_overview": False,
        "organic_count": len(result["organic_results"]),
        "ads_count": ads_count
    }
    
    return result

def fetch_serp_data(keyword: str, country_code: str, language_code: str) -> Dict[str, Any]:
    """
    Tries DataForSEO first. If it fails, falls back to SerpAPI.
    Returns structurally rich dictionary parsing URLs, PAA, elements, Knowledge graphs etc.
    """
    # Try DataForSEO
    dfs_data = call_dataforseo(keyword, country_code, language_code)
    if dfs_data and dfs_data.get("items"):
        return _parse_dataforseo_response(dfs_data)
        
    # Fallback to SerpAPI
    print("DataForSEO failed or returned empty. Falling back to SerpAPI...")
    serp_data = call_serpapi(keyword, country_code, language_code)
    if serp_data and serp_data.get("organic_results"):
        return _parse_serpapi_response(serp_data)
        
    raise Exception("Both SERP providers failed to return results.")
