import requests
import re

PROTOCOL_SUFFIX = "\n\nPlease output the exact filepath, followed by a markdown python code block."

def get_best_local_model() -> str | None:
    """
    Queries the local Ollama daemon for installed models and selects the best fit.
    Fails fast if Ollama is offline.
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        
        if not models:
            return None
            
        # Priority 1: Specifically tuned coding models
        # Priority 2: High-reasoning generalist models
        priorities = ["qwen", "deepseek", "coder", "llama", "phi"]
        
        for preferred in priorities:
            for model in models:
                if preferred in model.lower():
                    return model
                    
        # Fallback to the first available model if no priority matches
        return models[0]
        
    except requests.exceptions.RequestException:
        # Ollama is not running on this machine
        return None

def parse_llm_response(text: str):
    """Extracts filepath and sets a base confidence score."""
    filepath = "generated_code.py"
    path_match = re.search(r"(?:FILEPATH:|Targeting:?)\s*([a-zA-Z0-9_\-\./\\]+\.py)", text, re.IGNORECASE)
    if path_match:
        filepath = path_match.group(1).strip()
    return filepath, text, 0.9

def extract_code(text: str):
    """Extracts clean code from markdown blocks."""
    match = re.search(r"```(?:python)?(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

def run_local_with_confidence(task: str, context: dict) -> dict:
    """Executes a task against the dynamically selected local Ollama model."""
    model_name = get_best_local_model()
    
    if not model_name:
        print("[local model] Ollama offline or no models found. Instantly failing over to cloud...")
        return {"diff": "", "filepath": "generated_code.py", "confidence": 0.0}

    print(f"[local model] Selected dynamic model: {model_name}")
    
    prompt = task + PROTOCOL_SUFFIX
    system_prompt = context.get("system_prompt", "")
    
    payload = {
        "model": model_name,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False
    }
    
    try:
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=90)
        response.raise_for_status()
        content = response.json().get("response", "")
        
        filepath, code_text, confidence = parse_llm_response(content)
        clean_code = extract_code(code_text)
        
        return {
            "diff": clean_code,
            "filepath": filepath,
            "confidence": confidence
        }
    except requests.exceptions.RequestException as e:
        print(f"[local model] Execution failed: {e}")
        return {"diff": "", "filepath": "generated_code.py", "confidence": 0.0}