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

def fetch_serp_data(keyword: str, country_code: str, language_code: str) -> Dict[str, Any]:
    """
    Tries DataForSEO first. If it fails, falls back to SerpAPI.
    Returns standard dictionary with top urls, PAA and related searches.
    """
    result = {
        "source": "none",
        "urls": [],
        "paa": [],
        "related_searches": [],
        "raw_response": None
    }
    
    # Try DataForSEO
    dfs_data = call_dataforseo(keyword, country_code, language_code)
    if dfs_data and dfs_data.get("items"):
        result["source"] = "dataforseo"
        result["raw_response"] = dfs_data
        
        for item in dfs_data["items"]:
            if item.get("type") == "organic":
                url = item.get("url")
                if url:
                    result["urls"].append(url)
            elif item.get("type") == "people_also_ask":
                if item.get("items"):
                    for paa in item["items"]:
                        if isinstance(paa, dict):
                            title = paa.get("title") or paa.get("question") or paa.get("text")
                            if title:
                                result["paa"].append(title)
                        elif isinstance(paa, str) and paa.strip():
                            result["paa"].append(paa.strip())
            elif item.get("type") == "related_searches":
                if item.get("items"):
                    for rs in item["items"]:
                        if isinstance(rs, dict):
                            title = rs.get("title") or rs.get("query") or rs.get("text")
                            if title:
                                result["related_searches"].append(title)
                        elif isinstance(rs, str) and rs.strip():
                            result["related_searches"].append(rs.strip())
        
        return result
        
    # Fallback to SerpAPI
    print("DataForSEO failed or returned empty. Falling back to SerpAPI...")
    serp_data = call_serpapi(keyword, country_code, language_code)
    if serp_data and serp_data.get("organic_results"):
        result["source"] = "serpapi"
        result["raw_response"] = serp_data
        
        for item in serp_data["organic_results"]:
            result["urls"].append(item.get("link"))
            
        if "related_questions" in serp_data:
            result["paa"] = [q.get("question") for q in serp_data["related_questions"]]
            
        if "related_searches" in serp_data:
            result["related_searches"] = [rs.get("query") for rs in serp_data["related_searches"]]
            
        return result
        
    raise Exception("Both SERP providers failed to return results.")
