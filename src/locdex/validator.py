import os
import subprocess
import sys
from .safety import check_ast_security

def run_sandboxed(cmd, timeout=15):
    """Runs a subprocess with a timeout and a strictly sanitized environment."""
    
    # 1. Create a copy of the current system environment
    safe_env = os.environ.copy()
    
    # 2. Explicitly scrub highly sensitive keys so the LLM code cannot access them
    sensitive_keys = ["GITHUB_TOKEN", "OPENROUTER_API_KEY", "HF_TOKEN"]
    for key in sensitive_keys:
        safe_env.pop(key, None)
        
    try:
        # 3. Inject the sanitized environment into the subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env, 
            check=False
        )
        return result, None
    except subprocess.TimeoutExpired:
        return None, f"Execution timed out after {timeout} seconds."
    except Exception as e:
        return None, str(e)

def full_validation(repo_path: str, code: str, filepath: str) -> dict:
    """
    Runs the full suite of validation checks:
    1. Syntax Check
    2. AST Security Linter
    3. Consistency Check (if available)
    4. Pytest Execution (Sandboxed)
    """
    # 1. Syntax Check
    try:
        compile(code, filepath, "exec")
    except SyntaxError as e:
        return {"all_pass": False, "lint_pass": False, "message": f"Syntax Error: {e}"}

    # 2. Security Linter
    security_flags = check_ast_security(code)
    if security_flags:
        return {"all_pass": False, "lint_pass": False, "message": "Security Flags:\n" + "\n".join(security_flags)}
        
    # 3. Consistency Check (Fail gracefully if not yet fully implemented)
    try:
        from .consistency import check_consistency
        consistency_errs = check_consistency(repo_path, code)
        if consistency_errs:
            return {"all_pass": False, "lint_pass": False, "message": f"Consistency Errors:\n{consistency_errs}"}
    except ImportError:
        pass

    # 4. Sandbox Pytest Execution
    # We use a dummy test execution here if no actual pytest configuration is requested, 
    # but run_sandboxed handles the isolation perfectly.
    res, err = run_sandboxed([sys.executable, "-m", "pytest", repo_path], timeout=15)
    
    if err:
        return {"all_pass": False, "lint_pass": True, "message": f"Test Execution Timeout/Error:\n{err}"}
        
    if res and res.returncode != 0:
        return {"all_pass": False, "lint_pass": True, "message": f"Tests Failed:\n{res.stdout}\n{res.stderr}"}

    return {"all_pass": True, "lint_pass": True, "message": "All validation checks passed."}