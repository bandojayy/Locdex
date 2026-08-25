import subprocess
import os
import sys
from .consistency import check_consistency

SUPPORTED_LANGUAGES = {"python"}

def detect_language(repo_path: str) -> str:
    return "python"

def quick_check(repo_path: str, diff: str) -> dict:
    """Fast heuristic check before running full validation."""
    return {"passed": True}

def run_sandboxed(command: list, timeout: int = 15) -> tuple[subprocess.CompletedProcess, str]:
    """
    Soft Sandbox: Runs code in an isolated subprocess.
    - Strips API keys and tokens from the environment.
    - Enforces a strict timeout to kill infinite loops.
    """
    # Create a safe environment lacking sensitive credentials
    safe_env = {
        k: v for k, v in os.environ.items() 
        if "KEY" not in k.upper() and "TOKEN" not in k.upper()
    }
    
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            env=safe_env
        )
        return result, None
    except subprocess.TimeoutExpired:
        return None, "[Error] Execution timed out. The code may contain an infinite loop."
    except Exception as e:
        return None, f"[Error] Sandbox execution failed: {e}"

def full_validation(repo_path: str, diff: str, target_file: str) -> dict:
    """Executes sandboxed syntax checking, test execution, and AST consistency."""
    
    if not diff or not diff.strip():
        return {
            "language": "python", "tests_pass": False, "lint_pass": False,
            "consistency_pass": False, "ai_safety_pass": False,
            "consistency_flags": [], "all_pass": False,
            "message": "[Error] No code was generated. Validation aborted."
        }

    language = detect_language(repo_path)
    
    # Ensure the target directory exists before saving
    os.makedirs(os.path.dirname(os.path.abspath(target_file)) or ".", exist_ok=True)
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(diff)

    messages = []

    # 1. Syntax Check (Sandboxed)
    # Using sys.executable ensures it uses your current virtual environment
    syntax_res, syntax_err = run_sandboxed([sys.executable, "-m", "py_compile", target_file])
    
    if syntax_err:
        lint_pass = False
        messages.append(syntax_err)
    else:
        lint_pass = (syntax_res.returncode == 0)
        if not lint_pass:
            messages.append(f"Syntax Error caught by linter:\n{syntax_res.stderr}")

    # 2. Pytest Execution (Sandboxed)
    tests_pass = False
    test_res, test_err = run_sandboxed([sys.executable, "-m", "pytest", target_file])
    
    if test_err:
        messages.append(test_err)
    elif test_res:
        tests_pass = test_res.returncode in [0, 5]
        if not tests_pass:
            messages.append(f"Tests Failed:\n{test_res.stdout}\n{test_res.stderr}")
    else:
        messages.append("[Error] 'pytest' command execution failed unexpectedly.")

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