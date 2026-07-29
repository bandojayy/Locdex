import os
import json
import time

TELEMETRY_FILE = ".locdex_telemetry.json"

def is_telemetry_enabled() -> bool:
    """Checks if the user has explicitly opted into telemetry."""
    return os.environ.get("LOCDEX_TELEMETRY", "false").lower() == "true"

def log_routing_outcome(task_category: str, language: str, provider: str, success: bool, attempts: int):
    """
    Logs metadata about the routing outcome to a local file.
    Does NOT log the prompt, the code, or any proprietary context.
    """
    if not is_telemetry_enabled():
        return

    payload = {
        "timestamp": time.time(),
        "category": task_category,
        "language": language,
        "provider": provider,
        "success": success,
        "attempts": attempts
    }

    # Append to local JSON Lines file
    try:
        with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        print(f"[Telemetry] Warning: Could not write telemetry data: {e}")

def get_aggregated_stats() -> dict:
    """Reads local telemetry to inform future routing decisions."""
    if not os.path.exists(TELEMETRY_FILE):
        return {}
        
    stats = {}
    try:
        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                
                key = (data["language"], data["category"])
                if key not in stats:
                    stats[key] = {"attempts": 0, "successes": 0}
                    
                stats[key]["attempts"] += 1
                if data["success"]:
                    stats[key]["successes"] += 1
    except Exception:
        pass
        
    return stats