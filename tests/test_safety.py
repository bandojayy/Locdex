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
    malicious_code = "import os\nos.system('rm -rf /')"
    flags = check_ast_security(malicious_code)
    assert len(flags) > 0, "Failed to block malicious import."

def test_dangerous_function_call_blocked():
    """Verify that arbitrary execution functions like eval() are blocked."""
    malicious_code = "eval('print(hacked)')"
    flags = check_ast_security(malicious_code)
    assert len(flags) > 0, "Failed to block eval() execution."

def test_dynamic_import_bypass_blocked():
    """Verify that using __import__ to load 'os' is blocked."""
    malicious_code = "__import__('os').system('echo hacked')"
    flags = check_ast_security(malicious_code)
    assert len(flags) > 0, "Failed to block __import__('os') bypass."
    assert any("Dynamic execution bypass" in f or "built-in call" in f for f in flags)

def test_getattr_bypass_blocked():
    """Verify that using getattr to fetch 'eval' is blocked."""
    malicious_code = "getattr(__builtins__, 'eval')('print(1)')"
    flags = check_ast_security(malicious_code)
    assert len(flags) > 0, "Failed to block getattr(__builtins__, 'eval') bypass."

def test_builtins_access_blocked():
    """Verify that accessing the __builtins__ dict directly is blocked."""
    malicious_code = "f = __builtins__['eval']"
    flags = check_ast_security(malicious_code)
    assert len(flags) > 0, "Failed to block __builtins__ access."