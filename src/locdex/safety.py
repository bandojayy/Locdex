import ast
import os

DANGEROUS_IMPORTS = {"os", "subprocess", "sys", "pty", "socket", "shlex", "requests", "urllib", "importlib"}
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

            if func_name in {"getattr", "__import__", "import_module"}:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        val = arg.value
                        if val in DANGEROUS_CALLS or val in DANGEROUS_IMPORTS:
                            flags.append(f"[Security Violation] Dynamic execution bypass detected: attempting to load '{val}'.")

        elif isinstance(node, ast.Name):
            if node.id in {"__builtins__", "builtins"}:
                flags.append(f"[Security Violation] Access to the '{node.id}' namespace is strictly prohibited.")
                    
    return flags

def is_safe_path(base_dir: str, target_path: str) -> bool:
    """
    Verifies that a target file path resolves strictly within the allowed base directory.
    Prevents path traversal attacks (e.g., '../../Windows/System32/malware.exe').
    Also prevents CLI argument injection by blocking filenames starting with a hyphen.
    """
    try:
        # Prevent Git/CLI argument injection
        if os.path.basename(target_path).startswith("-"):
            return False
            
        abs_base = os.path.abspath(base_dir)
        abs_target = os.path.abspath(target_path)
        
        # os.path.commonpath ensures the target originates exactly from the base directory
        return os.path.commonpath([abs_base, abs_target]) == abs_base
    except ValueError:
        # Fails closed on Windows if paths are on different drives (e.g., C: vs D:)
        return False

def is_protected_path(target_path: str) -> bool:
    """
    Prevents the agent from overwriting sensitive internal files 
    even if they are technically inside the workspace.
    """
    try:
        # Get relative path from the current directory
        rel_path = os.path.relpath(target_path, ".")
        
        # Split the path into its individual folder/file components
        # Normalize slashes for Windows/Linux
        parts = set(rel_path.replace("\\", "/").split("/"))
        
        # Blacklisted directories and files
        protected_dirs = {".git", ".github", "venv", "env", ".env", "__pycache__", ".locdex_budget.json"}
        
        return bool(parts.intersection(protected_dirs))
    except ValueError:
        return True # Fail closed if path resolution fails