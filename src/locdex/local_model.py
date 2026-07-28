import requests
import re

import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3-coder:30b-a3b"

def run_local(prompt: str, system: str = "") -> dict:
    """Mode 1: Ollama, fully local, $0 per call."""
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "format": "json"
    })
    response.raise_for_status()
    return response.json()

def run_hosted_model(prompt: str, system: str = "") -> dict:
    """Mode 2: Modular hosted endpoint supporting OpenRouter and Gemini."""
    
    provider = os.environ.get("LOCDEX_HOSTED_PROVIDER", "openrouter").lower()
    
    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment.")
            
        # --- DYNAMIC FREE MODEL FETCHER ---
        try:
            print("\n[System] Querying OpenRouter for active free models...")
            models_req = requests.get("https://openrouter.ai/api/v1/models")
            models_req.raise_for_status()
            all_models = models_req.json().get("data", [])
            
            # Filter for models where both prompt and completion costs are exactly "0"
            free_models = [
                m["id"] for m in all_models 
                if m.get("pricing", {}).get("prompt") == "0" 
                and m.get("pricing", {}).get("completion") == "0"
            ]
            
            if not free_models:
                raise ValueError("No free models currently available on OpenRouter.")
                
            model_id = free_models[0] # Pick the first active one on the list
            print(f"[System] Success: Routing to {model_id}")
            
        except Exception as e:
            print(f"[System] Failed to fetch dynamic models: {e}")
            model_id = "mistralai/mistral-7b-instruct:free" # Ultimate fallback
        # ----------------------------------

        response = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/locdex", # OpenRouter recommends this header
            },
            json={
                "model": model_id,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            })
        response.raise_for_status()
        raw = response.json()
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"response": content, "raw": raw}
        
    elif provider == "gemini":
        # ... (keep your existing Gemini block here)
        pass

def get_configured_model_mode() -> str:
    """Defaults to hosted to bypass local hardware limits."""
    return os.environ.get("LOCDEX_MODE", "hosted")

def run_primary_model(prompt: str, system: str = "", mode: str = None) -> dict:
    """Single entry point the rest of the system calls."""
    mode = mode or get_configured_model_mode()  
    if mode == "hosted":
        return run_hosted_model(prompt, system)
    return run_local(prompt, system)

CONFIDENCE_SUFFIX = """

After writing the code above, on a new line, output exactly:
CONFIDENCE: <a number from 0.0 to 1.0 representing how confident you are this is correct and complete>
"""

def parse_confidence(raw_text: str) -> tuple[str, float]:
    """Splits the model's raw output into (code, confidence)."""
    match = re.search(r"CONFIDENCE:\s*([0-9.]+)", raw_text)
    confidence = float(match.group(1)) if match else 0.5
    confidence = max(0.0, min(1.0, confidence))  
    code = raw_text[:match.start()].rstrip() if match else raw_text
    return code, confidence

def extract_code(raw_text: str) -> str:
    """Strips Markdown formatting and extracts the pure code block."""
    # Looks for content inside ```python ... ``` or just ``` ... ```
    match = re.search(r"```(?:python)?\n(.*?)```", raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_text.strip()

def run_local_with_confidence(task: str, system: str = "") -> dict:
    """Single call that returns both generated code and confidence."""
    prompt = task + CONFIDENCE_SUFFIX
    raw = run_primary_model(prompt, system=system)
    
    raw_text = raw.get("response", "")
    code_with_confidence, confidence = parse_confidence(raw_text)
    
    # Clean the markdown formatting before returning the diff
    clean_code = extract_code(code_with_confidence)
    
    return {"diff": clean_code, "confidence": confidence, "raw": raw}