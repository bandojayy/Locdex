import os
import requests

CLOUD_PROVIDERS = {
    "claude-sonnet": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "key_env": "ANTHROPIC_API_KEY",
        "label": "Claude Sonnet",
    },
    "gpt-5": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "key_env": "OPENAI_API_KEY",
        "label": "GPT-5",
    },
    "deepseek-v3": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "key_env": "DEEPSEEK_API_KEY",
        "label": "DeepSeek V3",
    },
    "gemini": {
        "endpoint": "https://generativelanguage.googleapis.com/v1/models/gemini:generateContent",
        "key_env": "GOOGLE_API_KEY",
        "label": "Gemini",
    },
}

def available_providers() -> list[str]:
    """Only offer providers the user has actually configured a key for."""
    return [name for name, cfg in CLOUD_PROVIDERS.items() if os.environ.get(cfg["key_env"])]

DEFAULT_PROVIDER = "gemini"

def get_aggregated_provider_stats(language: str, category: str) -> dict:
    """Stub for telemetry lookup. Will be implemented in the telemetry phase."""
    return {}

def recommend_provider(category: str, language: str, min_samples: int = 50) -> str:
    """Recommends a provider based on telemetry, falls back to default if data is thin."""
    stats = get_aggregated_provider_stats(language, category)
    eligible = {p: s for p, s in stats.items() if s["sample_count"] >= min_samples}

    if not eligible:
        return DEFAULT_PROVIDER

    best = max(eligible, key=lambda p: eligible[p]["success_rate"])
    return best

def _call_provider(provider: str, cfg: dict, task: str, context: dict) -> dict:
    """Handles the unique HTTP payload shapes for different API endpoints."""
    api_key = os.environ.get(cfg["key_env"])
    headers = {"Content-Type": "application/json"}
    
    # Custom headers/payload mapping based on provider
    if provider == "claude-sonnet":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        payload = {
            "model": "claude-3-5-sonnet-20240620", 
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": task}]
        }
        if context and "system_prompt" in context:
            payload["system"] = context["system_prompt"]
    else:
        # Standard OpenAI-like payload
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": provider,
            "messages": [{"role": "user", "content": task}]
        }
        if context and "system_prompt" in context:
            payload["messages"].insert(0, {"role": "system", "content": context["system_prompt"]})
            
    response = requests.post(cfg["endpoint"], json=payload, headers=headers)
    response.raise_for_status()
    response = requests.post(cfg["endpoint"], json=payload, headers=headers)
    
    # --- GRACEFUL ERROR HANDLING ---
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"\n[Cloud Fallback] API Error ({provider}): {e}")
        return {"diff": "", "raw": {}, "provider": provider}
    # -------------------------------
    
    
    raw = response.json()
    
    # Extract output correctly depending on the provider
    content = ""
    if provider == "claude-sonnet":
        content = raw.get("content", [{}])[0].get("text", "")
    else:
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        
    return {"diff": content, "raw": raw, "provider": provider}

def run_cloud(task: str, context: dict, provider: str = None) -> dict:
    """Entry point for the router to escalate a task."""
    if provider is None:
        provider = recommend_provider(context.get("category"), context.get("language"))

    cfg = CLOUD_PROVIDERS.get(provider)
    if not cfg or not os.environ.get(cfg["key_env"]):
        raise ValueError(f"Provider '{provider}' isn't configured — set {cfg['key_env'] if cfg else '?'}")

    return _call_provider(provider, cfg, task, context)