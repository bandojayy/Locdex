import os
import requests
from .parser import MULTI_FILE_PROMPT, parse_multi_file_response

def run_cloud(task: str, context: dict = None) -> dict:
    """Executes a task against OpenRouter cloud models as a fallback."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("[Cloud Fallback] OPENROUTER_API_KEY not found. Cloud failover aborted.")
        return {"files": []}

    system_prompt = context.get("system_prompt", "") if context else ""
    prompt = task + MULTI_FILE_PROMPT

    # A robust chain of free OpenRouter models
    providers = [
        "deepseek/deepseek-r1:free",
        "qwen/qwen-2.5-coder-32b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "openrouter/free"
    ]

    for model in providers:
        print(f"[Cloud Fallback] Attempting provider: {model}...")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                print(f"[Cloud Fallback] ✓ Success using {model}")
                content = response.json()["choices"][0]["message"]["content"]
                files = parse_multi_file_response(content)
                return {"files": files}
            else:
                print(f"[Cloud Fallback] API Error {response.status_code} for {model}. Cycling to next provider...")
        except Exception as e:
            print(f"[Cloud Fallback] Request failed for {model}: {e}")

    print("[Cloud Fallback] All cloud providers failed.")
    return {"files": []}