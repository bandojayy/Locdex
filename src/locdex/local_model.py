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
            
        try:
            print("\n[System] Querying OpenRouter for active free models...")
            models_req = requests.get("https://openrouter.ai/api/v1/models")
            models_req.raise_for_status()
            all_models = models_req.json().get("data", [])
            
            free_models = [
                m["id"] for m in all_models 
                if m.get("pricing", {}).get("prompt") == "0" 
                and m.get("pricing", {}).get("completion") == "0"
            ]
            
            if not free_models:
                raise ValueError("No free models available on OpenRouter.")
                
            model_id = free_models[0] 
            print(f"[System] Success: Routing to {model_id}")
            
        except Exception as e:
            print(f"[System] Failed to fetch dynamic models: {e}")
            model_id = "mistralai/mistral-7b-instruct:free" 

        response = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/locdex",
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
        return {"response": "Error: Gemini block is empty. Switch to OpenRouter.", "raw": {}}
        
    return {"response": "Error: Provider not matched.", "raw": {}}

def get_configured_model_mode() -> str:
    return os.environ.get("LOCDEX_MODE", "hosted")

def run_primary_model(prompt: str, system: str = "", mode: str = None) -> dict:
    mode = mode or get_configured_model_mode()  
    if mode == "hosted":
        return run_hosted_model(prompt, system)
    return run_local(prompt, system)

# --- NEW PROTOCOL SUFFIX ---
PROTOCOL_SUFFIX = """

Before writing the code, on a new line, output the exact target file path in this format:
FILEPATH: <path/to/target_file.py>

Then provide the code block.

After the code block, on a new line, output exactly:
CONFIDENCE: <a number from 0.0 to 1.0 representing how confident you are>
"""

def parse_llm_response(raw_text: str) -> tuple[str, str, float]:
    """Extracts the target filepath, the code, and the confidence score."""
    # 1. Extract Filepath
    filepath_match = re.search(r"FILEPATH:\s*([^\n]+)", raw_text, re.IGNORECASE)
    filepath = filepath_match.group(1).strip() if filepath_match else "generated_code.py"
    
    # 2. Extract Confidence
    conf_match = re.search(r"CONFIDENCE:\s*([0-9.]+)", raw_text, re.IGNORECASE)
    confidence = float(conf_match.group(1)) if conf_match else 0.5
    confidence = max(0.0, min(1.0, confidence))
    
    # 3. Strip metadata to isolate the code block
    clean_text = raw_text
    if filepath_match:
        clean_text = clean_text.replace(filepath_match.group(0), "")
    if conf_match:
        clean_text = clean_text.replace(conf_match.group(0), "")
        
    return filepath, clean_text, confidence

def extract_code(raw_text: str) -> str:
    """Strips Markdown formatting and extracts the pure code block."""
    match = re.search(r"```(?:python)?\n(.*?)```", raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_text.strip()

def run_local_with_confidence(task: str, system: str = "") -> dict:
    prompt = task + PROTOCOL_SUFFIX
    raw = run_primary_model(prompt, system=system)
    
    raw_text = raw.get("response", "")
    filepath, code_text, confidence = parse_llm_response(raw_text)
    clean_code = extract_code(code_text)
    
    return {"filepath": filepath, "diff": clean_code, "confidence": confidence, "raw": raw}