import ast

# Added importlib to prevent dynamic module loading
DANGEROUS_IMPORTS = {"os", "subprocess", "sys", "pty", "socket", "shlex", "requests", "urllib", "importlib"}
# Added globals, locals, and __import__
DANGEROUS_CALLS = {"eval", "exec", "open", "__import__", "compile", "globals", "locals"}

def check_ast_security(code: str) -> list[str]:
    """
    Hardened AST parser. Detects direct malicious imports, built-in calls, 
    and dynamic execution bypasses (e.g., getattr, __import__).
    """
    flags = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return flags

    for node in ast.walk(tree):
        # 1. Block malicious direct imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_module = alias.name.split('.')[0]
                if base_module in DANGEROUS_IMPORTS:
                    flags.append(f"[Security Violation] Dangerous import detected: '{alias.name}'. Use of system/network modules is strictly prohibited.")
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split('.')[0]
                if base_module in DANGEROUS_IMPORTS:
                    flags.append(f"[Security Violation] Dangerous import detected: 'from {node.module} import ...'. Use of system/network modules is strictly prohibited.")
                    
        # 2. Block malicious calls and dynamic bypasses
        elif isinstance(node, ast.Call):
            func_name = None
            
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in DANGEROUS_CALLS:
                    flags.append(f"[Security Violation] Dangerous built-in call detected: '{func_name}()'. Arbitrary code execution is blocked.")
            
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
                if func_name in DANGEROUS_CALLS:
                    flags.append(f"[Security Violation] Dangerous attribute call detected: '{func_name}()'.")
                if isinstance(node.func.value, ast.Name) and node.func.value.id in DANGEROUS_IMPORTS:
                    flags.append(f"[Security Violation] Dangerous module call detected: '{node.func.value.id}.{func_name}()'.")

            # Deep Inspection: Catch getattr(__builtins__, 'eval') or __import__('os')
            if func_name in {"getattr", "__import__", "import_module"}:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        val = arg.value
                        if val in DANGEROUS_CALLS or val in DANGEROUS_IMPORTS:
                            flags.append(f"[Security Violation] Dynamic execution bypass detected: attempting to load '{val}'.")

        # 3. Block direct access to the builtins namespace
        elif isinstance(node, ast.Name):
            if node.id in {"__builtins__", "builtins"}:
                flags.append(f"[Security Violation] Access to the '{node.id}' namespace is strictly prohibited.")
                    
    return flags