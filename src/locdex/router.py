from .local_model import run_local_with_confidence
from .cloud_fallback import run_cloud
from .validator import full_validation

def route_task(task: str, task_type: str, context: dict, thresholds: dict) -> dict:
    attempts = 3
    last_error = ""
    
    for attempt in range(1, attempts + 1):
        print(f"[Router] Attempt {attempt}/{attempts}...")
        
        result = run_local_with_confidence(f"{task}\n{last_error}", **context)
        
        if not result or result.get("confidence", 1.0) == 0.0 or not result.get("files"):
            print("[Router] Local model unavailable or failed. Escalating to Cloud...")
            cloud_res = run_cloud(f"{task}\n{last_error}", context)
            return {"source": "cloud", "result": cloud_res}
            
        all_pass = True
        error_msgs = []
        for f in result.get("files", []):
            val = full_validation(".", f["code"], f["filepath"])
            if not val["all_pass"]:
                all_pass = False
                error_msgs.append(f"{f['filepath']}: {val['message']}")
                
        if all_pass:
            return {"source": "local", "result": result}
        else:
            last_error = "Validation failed:\n" + "\n".join(error_msgs)
            print(f"[Router] Validation failed on attempt {attempt}. Retrying...")
            
    print("[Router] Local auto-healing exhausted. Escalating to Cloud...")
    final_cloud = run_cloud(task, context)
    return {"source": "cloud", "result": final_cloud}