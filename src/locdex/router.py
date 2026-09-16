from .local_model import run_local_with_confidence
from .cloud_fallback import run_cloud
from .validator import full_validation, quick_check

def route_task(task: str, task_type: str, context: dict, thresholds: dict) -> dict:
    """
    Routes the task to the local model first. If it fails, or if validation fails 
    3 times, it safely escalates to the cloud fallback chain.
    """
    attempts = 3
    last_error = ""
    
    for attempt in range(1, attempts + 1):
        print(f"[Router] Attempt {attempt}/{attempts}...")
        
        # 1. Try Local Model
        result = run_local_with_confidence(f"{task}\n{last_error}", **context)
        
        # 2. If Local fails completely (Ollama offline), switch to Cloud instantly
        if not result or result.get("confidence", 1.0) == 0.0 or not result.get("diff"):
            print("[Router] Local model unavailable or failed. Escalating to Cloud...")
            cloud_res = run_cloud(f"{task}\n{last_error}", context)  # <-- FIXED
            return {"source": "cloud", "result": cloud_res}
            
        # 3. Soft Sandbox Validation loop
        val = full_validation(".", result.get("diff", ""), result.get("filepath", "generated_code.py"))
        if val["all_pass"]:
            return {"source": "local", "result": result}
        else:
            last_error = f"Validation failed: {val['message']}. Please fix the code."
            print(f"[Router] Validation failed on attempt {attempt}. Retrying...")
            
    # If we exhaust all local attempts, do one final cloud fallback
    print("[Router] Local auto-healing exhausted. Escalating to Cloud...")
    final_cloud = run_cloud(task, context)  # <-- FIXED
    return {"source": "cloud", "result": final_cloud}