import os
import time
from typing import Dict, Any, List, Optional, Tuple
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
    max_tokens: Optional[int] = None,
    max_retries: int = 3,
    response_format: Optional[Dict[str, str]] = None
) -> Tuple[str, float, str, Optional[Dict[str, Any]]]:
    """
    Generic LLM call with retry policy. Returns (generated_text, estimated_cost, actual_model, usage_or_none).
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
            if max_tokens is not None and max_tokens > 0:
                kwargs["max_tokens"] = max_tokens
            if response_format:
                 kwargs["response_format"] = response_format
                 
            raw_response = client.chat.completions.with_raw_response.create(**kwargs)
            response = raw_response.parse()
            
            # Simple fallback cost estimation if headers/model logic isn't perfectly transparent
            cost = 0.0
            
            # Try to grab exact cost from OpenRouter headers
            openrouter_cost = raw_response.headers.get("x-openrouter-cost")
            if openrouter_cost:
                try:
                    cost = float(openrouter_cost)
                except (ValueError, TypeError):
                    cost = 0.0
                    
            if cost == 0.0 and response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                # Very rough generic estimation: ~ $0.15/1M input, ~ $0.60/1M output (like gpt-4o-mini rates)
                if "gpt-4o-mini" in model:
                    cost = (prompt_tokens * 0.15 / 1000000) + (completion_tokens * 0.60 / 1000000)
                elif "gemini-3" in model or "gemini-2.5" in model:
                    cost = (prompt_tokens * 0.075 / 1000000) + (completion_tokens * 0.30 / 1000000)
                else: 
                    # Default tiny rate to still show it's tracking
                    cost = (prompt_tokens * 0.1 / 1000000) + (completion_tokens * 0.5 / 1000000)
                    
            actual_model = getattr(response, "model", None) or model
            usage_info: Optional[Dict[str, Any]] = None
            if response.usage:
                usage_info = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            return response.choices[0].message.content, cost, actual_model, usage_info
            
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
