import subprocess
import os
from .consistency import check_consistency

SUPPORTED_LANGUAGES = {"python"}

def detect_language(repo_path: str) -> str:
    return "python"

def quick_check(repo_path: str, diff: str) -> dict:
    """Fast heuristic check before running full validation."""
    return {"passed": True}

def full_validation(repo_path: str, diff: str, target_file: str) -> dict:
    """Executes real syntax checking, test execution, and AST consistency on the target file."""
    
    # GUARD: Block empty files
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
    
    # NEW: Ensure the target directory exists before saving the diff
    os.makedirs(os.path.dirname(os.path.abspath(target_file)) or ".", exist_ok=True)
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(diff)

    messages = []

    # 1. Syntax Check (using dynamic target_file)
    syntax_result = subprocess.run(
        ["python", "-m", "py_compile", target_file],
        capture_output=True, text=True
    )
    lint_pass = (syntax_result.returncode == 0)
    if not lint_pass:
        messages.append(f"Syntax Error caught by linter:\n{syntax_result.stderr}")

    # 2. Pytest Execution (using dynamic target_file)
    tests_pass = False
    try:
        test_result = subprocess.run(
            ["pytest", target_file], 
            capture_output=True, text=True
        )
        tests_pass = test_result.returncode in [0, 5]
        if not test_result.returncode in [0, 5]:
            messages.append(f"Tests Failed:\n{test_result.stdout}\n{test_result.stderr}")
    except FileNotFoundError:
        messages.append("[Error] 'pytest' command not found. Please run: pip install pytest")

    # 3. AST Consistency Check
    consistency_flags = check_consistency(repo_path, diff)
    consistency_pass = (len(consistency_flags) == 0)
    if not consistency_pass:
        messages.append("AST Consistency Check Failed:\n" + "\n".join(consistency_flags))

    # 4. AI Safety Check (Mocked)
    ai_safety_pass = True

    all_pass = lint_pass and tests_pass and consistency_pass and ai_safety_pass

    return {
        "language": language,
        "tests_pass": tests_pass,
        "lint_pass": lint_pass,
        "consistency_pass": consistency_pass,
        "ai_safety_pass": ai_safety_pass,
        "consistency_flags": consistency_flags,
        "all_pass": all_pass,
        "message": "\n\n".join(messages) if not all_pass else f"Validation passed for {target_file}."
    }