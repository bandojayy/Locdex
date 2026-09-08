import sys
from src.locdex.validator import run_sandboxed, full_validation

def test_run_sandboxed_success():
    """Verify that a safe, fast subprocess executes correctly."""
    res, err = run_sandboxed([sys.executable, "-c", "print('sandbox test')"], timeout=5)
    assert err is None, "Sandbox should not return an error for valid code."
    assert res.returncode == 0
    assert "sandbox test" in res.stdout

def test_run_sandboxed_timeout():
    """Verify that infinite loops or long-running processes are strictly killed."""
    # We tell Python to sleep for 3 seconds, but restrict the sandbox to 1 second
    res, err = run_sandboxed([sys.executable, "-c", "import time; time.sleep(3)"], timeout=1)
    
    assert res is None, "Result should be None when a timeout occurs."
    assert err is not None
    assert "Execution timed out" in err, "Sandbox failed to kill the hanging process."

def test_full_validation_syntax_error():
    """Verify that invalid Python syntax fails the validation gate instantly."""
    bad_code = "def missing_colon() print('this is bad syntax')"
    
    # Run validation on the bad code
    result = full_validation(".", bad_code, "dummy.py")
    
    assert result["all_pass"] is False, "Validation gate incorrectly passed invalid syntax."
    assert result["lint_pass"] is False
    assert "Syntax Error" in result["message"]