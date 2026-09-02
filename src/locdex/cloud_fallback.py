import os
import requests
import time
from .local_model import PROTOCOL_SUFFIX, parse_llm_response, extract_code

# Prioritized chain of high-quality free models on OpenRouter
FALLBACK_CHAIN = [
    "deepseek/deepseek-r1:free",                 # Top-tier reasoning and coding
    "qwen/qwen-2.5-coder-32b-instruct:free",     # Stable, highly available open-weight coder
    "meta-llama/llama-3.3-70b-instruct:free",    # Reliable, highly available generalist
    "openrouter/free"                            # Automatic dynamic routing to ANY available free model
]

def _call_openrouter(model_id: str, prompt: str, system: str, api_key: str) -> dict:
    """Makes a discrete call to OpenRouter with a specific model."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/locdex",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    if system:
        payload["messages"].insert(0, {"role": "system", "content": system})
            
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions", 
        json=payload, 
        headers=headers,
        timeout=45
    )
    response.raise_for_status()
    return response.json()

def run_cloud(task: str, context: dict) -> dict:
    """
    Intelligent cloud fallback system. Iterates through a prioritized list of free
    OpenRouter models. Gracefully cycles on rate limits (429) or missing models (404).
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\n[Cloud Fallback] Error: OPENROUTER_API_KEY environment variable not set.")
        return {"filepath": "generated_code.py", "diff": "", "raw": {}, "provider": "failed"}

    prompt = task + PROTOCOL_SUFFIX
    system_prompt = context.get("system_prompt", "")
    
    # Failover Loop
    for model_id in FALLBACK_CHAIN:
        print(f"[Cloud Fallback] Attempting provider: {model_id}...")
        try:
            raw = _call_openrouter(model_id, prompt, system_prompt, api_key)
            
            content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse the structured response
            filepath, code_text, confidence = parse_llm_response(content)
            clean_code = extract_code(code_text)
            
            print(f"[Cloud Fallback] ✓ Success using {model_id}")
            return {
                "filepath": filepath, 
                "diff": clean_code, 
                "raw": raw, 
                "provider": model_id
            }
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                print(f"[Cloud Fallback] Unauthorized API Key (401). Aborting cloud fallback.")
                break # Only break if the API key is completely rejected
            elif status_code == 429:
                print(f"[Cloud Fallback] Rate limit (429) hit for {model_id}. Cycling to next provider...")
                time.sleep(1)
                continue
            else:
                # NEW: Catch 404s, 403s, 500s and gracefully continue to the next model
                print(f"[Cloud Fallback] API Error {status_code} for {model_id}. Cycling to next provider...")
                continue
                
        except requests.exceptions.RequestException as e:
            print(f"[Cloud Fallback] Network error contacting {model_id}: {e}")
            continue # Try next model if network connection fails

    print("[Cloud Fallback] ❌ All fallback providers exhausted.")
    return {"filepath": "generated_code.py", "diff": "", "raw": {}, "provider": "failed"}