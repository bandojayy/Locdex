import ast
import os

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules", "env"}

def get_definitions(code_str: str) -> set:
    """Parses Python code and extracts all function and class names."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return set()
        
    definitions = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.add(node.name)
    return definitions

def check_consistency(repo_path: str, generated_code: str) -> list[str]:
    """
    Scans the workspace to ensure the generated code doesn't 
    redefine or shadow existing project architecture.
    """
    flags = []
    
    # 1. What does the AI want to define?
    new_definitions = get_definitions(generated_code)
    if not new_definitions:
        return flags

    # 2. What already exists in the workspace?
    workspace_definitions = set()
    for root, dirs, files in os.walk(repo_path):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for file in files:
            if file.endswith('.py') and file != "generated_code.py":
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        workspace_definitions.update(get_definitions(f.read()))
                except Exception:
                    pass
    
    # 3. Check for collisions
    collisions = new_definitions.intersection(workspace_definitions)
    for collision in collisions:
        flags.append(f"Naming Collision: '{collision}' is already defined in your workspace.")
        
    return flags