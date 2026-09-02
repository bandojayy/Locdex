from src.locdex.safety import check_ast_security

def test_safe_code_passes():
    """Verify that standard, harmless code passes the linter without flags."""
    safe_code = """
def add_numbers(a, b):
    return a + b
print(add_numbers(5, 10))
    """
    flags = check_ast_security(safe_code)
    assert len(flags) == 0, "Safe code should not generate any security flags."

def test_dangerous_import_blocked():
    """Verify that importing system modules is blocked."""
    malicious_code = """
import os
os.system("rm -rf /")
    """
    flags = check_ast_security(malicious_code)
    assert len(flags) > 0, "Failed to block malicious import."
    assert any("Dangerous import detected" in flag for flag in flags)

def test_dangerous_function_call_blocked():
    """Verify that arbitrary execution functions like eval() are blocked."""
    malicious_code = """
user_input = "print('hacked')"
eval(user_input)
    """
    flags = check_ast_security(malicious_code)
    assert len(flags) > 0, "Failed to block eval() execution."
    assert any("Dangerous built-in call detected" in flag for flag in flags)