import os
from .local_model import run_local_with_confidence
from .cloud_fallback import run_cloud
from .validator import quick_check, full_validation, detect_language
from .consistency import check_consistency

MAX_LOCAL_ATTEMPTS = 2
CONFIDENCE_THRESHOLD = 0.0

def should_escalate(language: str, category: str, confidence: float, validation: dict,
                     category_thresholds: dict) -> tuple[bool, str]:
    if category_thresholds.get((language, category), MAX_LOCAL_ATTEMPTS) == 0:
        return True, "category_threshold_zero"

    if confidence < CONFIDENCE_THRESHOLD:
        return True, "low_confidence"

    if not validation.get("tests_pass", False) or not validation.get("lint_pass", False):
        return True, "hard_failure"

    if validation.get("consistency_flags"):
        return True, "consistency_risk"

    return False, "local_sufficient"


def route_task(task: str, category: str, context: dict, category_thresholds: dict) -> dict:
    language = detect_language(context.get("repo_path", "."))  
    allowed_attempts = category_thresholds.get((language, category), MAX_LOCAL_ATTEMPTS)
    reason = "local_sufficient"

    for attempt in range(allowed_attempts):
        result = run_local_with_confidence(task, system=context.get("system_prompt", ""))
        
        # --- NEW: Extract the dynamic target file from the model's result ---
        target_file = result.get("filepath", "generated_code.py")

        if quick_check(context.get("repo_path", "."), result["diff"]):
            # --- NEW: Pass target_file into the autonomous validation check ---
            validation = full_validation(context.get("repo_path", "."), result["diff"], target_file)
            
            escalate, reason = should_escalate(language, category, result.get("confidence", 0.5),
                                               validation, category_thresholds)
            if not escalate:
                return {"source": "local", "result": result, "attempts": attempt + 1,
                        "confidence": result.get("confidence", 0.5), "language": language,
                        "escalation_reason": None}

    # Exhausted local attempts, fallback to cloud
    result = run_cloud(task, context)
    return {"source": "cloud", "result": result, "escalation_reason": reason}