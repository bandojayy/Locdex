import requests
from .parser import MULTI_FILE_PROMPT, parse_multi_file_response

def get_best_local_model() -> str | None:
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        if not models: return None
            
        priorities = ["qwen", "deepseek", "coder", "llama", "phi"]
        for preferred in priorities:
            for model in models:
                if preferred in model.lower():
                    return model
        return models[0]
    except requests.exceptions.RequestException:
        return None

def run_local_with_confidence(task: str, system: str = "", context: dict = None, **kwargs) -> dict:
    model_name = get_best_local_model()
    if not model_name:
        print("[local model] Ollama offline or no models found. Instantly failing over to cloud...")
        return {"files": [], "confidence": 0.0}

    print(f"[local model] Selected dynamic model: {model_name}")
    
    prompt = task + MULTI_FILE_PROMPT
    system_prompt = system if system else (context.get("system_prompt", "") if context else "")
    
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
        
        files = parse_multi_file_response(content)
        confidence = 0.9 if files else 0.0
        
        return {"files": files, "confidence": confidence}
    except requests.exceptions.RequestException as e:
        print(f"[local model] Execution failed: {e}")
        return {"files": [], "confidence": 0.0}