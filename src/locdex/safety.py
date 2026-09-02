import ast

DANGEROUS_IMPORTS = {"os", "subprocess", "sys", "pty", "socket", "shlex", "requests", "urllib"}
DANGEROUS_CALLS = {"eval", "exec", "open", "__import__", "compile"}

def check_ast_security(code: str) -> list[str]:
    """
    Parses Python code into an AST and detects dangerous imports or built-in function calls.
    Returns a list of security flags. An empty list means the code is safe to execute.
    """
    flags = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # We don't flag syntax errors here; the py_compile linting step handles that.
        return flags

    for node in ast.walk(tree):
        # Block malicious imports: import os
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_module = alias.name.split('.')[0]
                if base_module in DANGEROUS_IMPORTS:
                    flags.append(f"[Security Violation] Dangerous import detected: '{alias.name}'. Use of system/network modules is strictly prohibited.")
        
        # Block malicious from-imports: from os import system
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split('.')[0]
                if base_module in DANGEROUS_IMPORTS:
                    flags.append(f"[Security Violation] Dangerous import detected: 'from {node.module} import ...'. Use of system/network modules is strictly prohibited.")
                    
        # Block malicious built-in function calls: eval() or exec()
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in DANGEROUS_CALLS:
                    flags.append(f"[Security Violation] Dangerous built-in call detected: '{node.func.id}()'. Arbitrary code execution is blocked.")
            
            # Block attribute calls on bypassed modules (defense-in-depth): os.system()
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in DANGEROUS_CALLS:
                    flags.append(f"[Security Violation] Dangerous attribute call detected: '{node.func.attr}()'.")
                if isinstance(node.func.value, ast.Name) and node.func.value.id in DANGEROUS_IMPORTS:
                    flags.append(f"[Security Violation] Dangerous module call detected: '{node.func.value.id}.{node.func.attr}()'.")
                    
    return flags