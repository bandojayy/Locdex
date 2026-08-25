import json
import os

BUDGET_FILE = ".locdex_budget.json"
# Benchmark against Claude 3.5 Sonnet / GPT-4o standard pricing
CLOUD_COST_PER_1M_IN = 3.00
CLOUD_COST_PER_1M_OUT = 15.00

def load_budget() -> dict:
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_spent": 0.0, "total_saved": 0.0, "local_calls": 0, "cloud_calls": 0}

def save_budget(data: dict):
    with open(BUDGET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def record_usage(source: str, prompt: str, generated_text: str):
    """Calculates token costs and updates the ledger."""
    budget = load_budget()
    
    # Standard heuristic: ~4 characters per token
    in_tokens = len(prompt) / 4.0
    out_tokens = len(generated_text) / 4.0
    
    cost = (in_tokens / 1_000_000) * CLOUD_COST_PER_1M_IN + (out_tokens / 1_000_000) * CLOUD_COST_PER_1M_OUT
    
    if source == "local":
        budget["total_saved"] += cost
        budget["local_calls"] += 1
    else:
        budget["total_spent"] += cost
        budget["cloud_calls"] += 1
        
    save_budget(budget)

def get_metrics_report() -> str:
    """Returns formatted string of session economics."""
    b = load_budget()
    return (
        f"\n--- Locdex Budget Metrics ---\n"
        f"Local Generations: {b['local_calls']} (Saved: ${b['total_saved']:.4f})\n"
        f"Cloud Fallbacks:   {b['cloud_calls']} (Spent: ${b['total_spent']:.4f})\n"
        f"---------------------------\n"
    )