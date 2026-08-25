import os
from .local_model import run_local_with_confidence
from .cloud_fallback import run_cloud
from .validator import quick_check, full_validation, detect_language
from .consistency import check_consistency
from .planner import record_usage

MAX_LOCAL_ATTEMPTS = 3

def route_task(task: str, category: str, context: dict, category_thresholds: dict) -> dict:
    language = detect_language(context.get("repo_path", "."))  
    allowed_attempts = category_thresholds.get((language, category), MAX_LOCAL_ATTEMPTS)
    
    current_prompt = task
    reason = "local_sufficient"

    for attempt in range(allowed_attempts):
        print(f"[Router] Attempt {attempt + 1}/{allowed_attempts}...")
        
        result = run_local_with_confidence(current_prompt, system=context.get("system_prompt", ""))
        target_file = result.get("filepath", "generated_code.py")
        
        # --- METRICS: Log the local generation savings ---
        generated_text = result.get("raw", {}).get("response", result.get("diff", ""))
        record_usage("local", current_prompt, generated_text)

        if quick_check(context.get("repo_path", "."), result["diff"]):
            validation = full_validation(context.get("repo_path", "."), result["diff"], target_file)
            
            if validation.get("all_pass"):
                return {
                    "source": "local", 
                    "result": result, 
                    "attempts": attempt + 1,
                    "confidence": result.get("confidence", 0.5), 
                    "language": language,
                    "escalation_reason": None
                }
            else:
                print(f"[Router] Validation failed. Auto-healing...")
                reason = "hard_failure" if not validation.get("lint_pass") or not validation.get("tests_pass") else "consistency_risk"
                
                error_feedback = validation.get("message", "Unknown error")
                current_prompt = (
                    f"{task}\n\n--- PREVIOUS ATTEMPT FAILED ---\n"
                    f"The code you just generated failed automated validation with these errors:\n\n{error_feedback}\n\n"
                    f"Please fix these errors and rewrite the code. Remember to include FILEPATH: and CONFIDENCE:."
                )
        else:
            reason = "quick_check_failed"

    print("[Router] Local attempts exhausted. Escalating to cloud model...")
    cloud_result = run_cloud(current_prompt, context)
    
    # --- METRICS: Log the cloud API spend ---
    record_usage("cloud", current_prompt, cloud_result.get("diff", ""))
    
    return {"source": "cloud", "result": cloud_result, "escalation_reason": reason}