import subprocess
import os
from .consistency import check_consistency

SUPPORTED_LANGUAGES = {"python"}

def detect_language(repo_path: str) -> str:
    return "python"

def quick_check(repo_path: str, diff: str) -> dict:
    """Fast heuristic check before running full validation."""
    return {"passed": True}

def full_validation(repo_path: str, diff: str) -> dict:
    """Executes real syntax checking, test execution, and AST consistency."""

    # --- NEW GUARD: BLOCK EMPTY FILES ---
    if not diff or not diff.strip():
        return {
            "language": "python",
            "tests_pass": False,
            "lint_pass": False,
            "consistency_pass": False,
            "ai_safety_pass": False,
            "consistency_flags": [],
            "all_pass": False,
            "message": "[Error] No code was generated. Validation aborted."
        }
    language = detect_language(repo_path)
    file_to_check = "generated_code.py"
    
    # Ensure the file exists with the latest diff
    if not os.path.exists(file_to_check) or diff:
        with open(file_to_check, "w", encoding="utf-8") as f:
            f.write(diff)

    messages = []

    # 1. Syntax Check (Lint Proxy)
    syntax_result = subprocess.run(
        ["python", "-m", "py_compile", file_to_check],
        capture_output=True, text=True
    )
    lint_pass = (syntax_result.returncode == 0)
    if not lint_pass:
        messages.append(f"Syntax Error caught by linter:\n{syntax_result.stderr}")

    # 2. Pytest Execution
    tests_pass = False
    try:
        test_result = subprocess.run(
            ["pytest", file_to_check], 
            capture_output=True, text=True
        )
        tests_pass = test_result.returncode in [0, 5]
        if not tests_pass:
            messages.append(f"Tests Failed:\n{test_result.stdout}\n{test_result.stderr}")
    except FileNotFoundError:
        messages.append("[Error] 'pytest' command not found. Please run: pip install pytest")

    # 3. AST Consistency Check
    consistency_flags = check_consistency(repo_path, diff)
    consistency_pass = (len(consistency_flags) == 0)
    if not consistency_pass:
        messages.append("AST Consistency Check Failed:\n" + "\n".join(consistency_flags))

    # 4. AI Safety Check (Mocked for now)
    ai_safety_pass = True

    # STRICT FAIL-CLOSED LOGIC
    all_pass = lint_pass and tests_pass and consistency_pass and ai_safety_pass

    return {
        "language": language,
        "tests_pass": tests_pass,
        "lint_pass": lint_pass,
        "consistency_pass": consistency_pass,
        "ai_safety_pass": ai_safety_pass,
        "consistency_flags": consistency_flags,
        "all_pass": all_pass,
        "message": "\n\n".join(messages) if not all_pass else "Validation passed."
    }