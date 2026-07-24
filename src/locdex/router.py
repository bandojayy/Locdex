from .local_model import run_local_with_confidence
from .cloud_fallback import run_cloud
# Note: We will build validator.py and consistency.py in the next steps!
from .validator import quick_check, full_validation, detect_language
from .consistency import check_consistency

MAX_LOCAL_ATTEMPTS = 2
CONFIDENCE_THRESHOLD = 0.6

def should_escalate(language: str, category: str, confidence: float, validation: dict,
                     category_thresholds: dict) -> tuple[bool, str]:
    # Trigger 1: Threshold says skip local entirely based on past aggregate data
    if category_thresholds.get((language, category), MAX_LOCAL_ATTEMPTS) == 0:
        return True, "category_threshold_zero"

    # Trigger 2: The model self-reported low confidence
    if confidence < CONFIDENCE_THRESHOLD:
        return True, "low_confidence"

    # Trigger 3: Hard failure — code doesn't compile or fails lint/tests
    if not validation.get("tests_pass", False) or not validation.get("lint_pass", False):
        return True, "hard_failure"

    # Trigger 4: Consistency check flagged incompatible call sites elsewhere in the repo
    if validation.get("consistency_flags"):
        return True, "consistency_risk"

    return False, "local_sufficient"


def route_task(task: str, category: str, context: dict, category_thresholds: dict) -> dict:
    # Detect if we are working with Python, TypeScript, Go, etc.
    language = detect_language(context.get("repo_path", "."))  
    allowed_attempts = category_thresholds.get((language, category), MAX_LOCAL_ATTEMPTS)
    reason = "local_sufficient"

    for attempt in range(allowed_attempts):
        result = run_local_with_confidence(task, system=context.get("system_prompt", ""))

        # Only run the heavy validation if the quick syntax check passes
        if quick_check(result, task):
            validation = full_validation(context.get("repo_path", "."), result["diff"])
            escalate, reason = should_escalate(language, category, result["confidence"],
                                                validation, category_thresholds)
            if not escalate:
                return {"source": "local", "result": result, "attempts": attempt + 1,
                        "confidence": result["confidence"], "language": language,
                        "escalation_reason": None}

    # Exhausted local attempts, or an explicit trigger fired early
    result = run_cloud(task, context)
    return {"source": "cloud", "result": result, "escalation_reason": reason}