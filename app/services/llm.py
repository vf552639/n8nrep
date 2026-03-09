import os
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI
from app.config import settings

_openai_client = None

def get_openai_client() -> OpenAI:
    """Returns an OpenAI client configured for OpenRouter (Singleton)"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
    return _openai_client

def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str = settings.DEFAULT_MODEL,
    temperature: float = 0.7,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    top_p: float = 1.0,
    max_retries: int = 3,
    response_format: Optional[Dict[str, str]] = None
) -> str:
    """
    Generic LLM call with retry policy
    """
    client = get_openai_client()
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    last_error = None
    retries = 0
    while retries < max_retries:
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty,
                "top_p": top_p,
                "extra_headers": {
                    "HTTP-Referer": "https://example.com", # Update logically later
                    "X-Title": "SEO-Generator"
                }
            }
            if response_format:
                 kwargs["response_format"] = response_format
                 
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
            
        except Exception as e:
            last_error = str(e)
            error_msg = str(e)
            print(f"LLM Error (Attempt {retries+1}/{max_retries}): {error_msg}")
            
            # Rate limit or server error logic
            if "429" in error_msg or "rate limit" in error_msg.lower():
                time.sleep(60 * (retries + 1))  # Exponential backoff: 60s, 120s, 180s
            elif "502" in error_msg or "504" in error_msg or "timeout" in error_msg.lower():
                time.sleep((retries + 1) * 15)  # 15s, 30s, 45s
            else:
                 # If unexpected error, maybe retry faster
                 time.sleep(5)
                 
            retries += 1
            
    raise Exception(
        f"LLM Generation failed after {max_retries} attempts. "
        f"Model: {model}. Last error: {last_error}"
    )
