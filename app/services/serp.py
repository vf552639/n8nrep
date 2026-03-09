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

def call_dataforseo(keyword: str, location_code: str, language_code: str) -> Optional[Dict[str, Any]]:
    url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
    headers = {
        'Authorization': _get_dataforseo_auth_header(),
        'Content-Type': 'application/json'
    }
    payload = [{
        "keyword": keyword,
        "location_code": int(location_code) if location_code.isdigit() else 2840, # default US if not valid
        "language_code": language_code,
        "depth": 10
    }]
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("tasks") and len(data["tasks"]) > 0:
            return data["tasks"][0]["result"][0]
        return None
    except Exception as e:
        print(f"DataForSEO error: {e}")
        return None

def call_serpapi(keyword: str, location: str, language: str) -> Optional[Dict[str, Any]]:
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": keyword,
        "location": location,
        "hl": language,
        "num": 10,
        "api_key": settings.SERPAPI_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
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
                result["urls"].append(item.get("url"))
            elif item.get("type") == "people_also_ask":
                if item.get("items"):
                    result["paa"].extend([paa.get("title") for paa in item["items"] if paa.get("title")])
            elif item.get("type") == "related_searches":
                if item.get("items"):
                    result["related_searches"].extend([rs.get("title") for rs in item["items"] if rs.get("title")])
        
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
