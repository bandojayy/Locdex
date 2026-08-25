import os
import ast

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules", "env", ".pytest_cache"}
MAX_CONTEXT_LENGTH = 15000

def extract_skeleton(filepath: str) -> str:
    """
    Parses a Python file and returns a structural skeleton 
    (classes, methods, functions, and docstrings) instead of raw code.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        tree = ast.parse(content)
        skeleton = []
        
        for node in tree.body:
            # Extract Functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [arg.arg for arg in node.args.args]
                args_str = ", ".join(args)
                skeleton.append(f"def {node.name}({args_str}): ...")
            
            # Extract Classes and their internal methods
            elif isinstance(node, ast.ClassDef):
                skeleton.append(f"class {node.name}:")
                has_methods = False
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [arg.arg for arg in item.args.args]
                        skeleton.append(f"    def {item.name}({', '.join(args)}): ...")
                        has_methods = True
                if not has_methods:
                    skeleton.append("    pass")
                    
        if skeleton:
            return "\n".join(skeleton)
            
        # If it's a script with no functions, return a tiny snippet
        return content[:200] + "\n... (raw script omitted)"
        
    except SyntaxError:
        return "<SyntaxError: unparseable file>"
    except Exception as e:
        return f"<Error reading file: {e}>"

def get_workspace_context(repo_path: str) -> str:
    """
    Sweeps the workspace and builds a complete architectural map 
    using AST skeletons to preserve token limits.
    """
    context = []
    char_count = 0

    for root, dirs, files in os.walk(repo_path):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                
                # Use the new semantic chunking
                skeleton = extract_skeleton(filepath)
                
                file_context = f"\n--- {filepath} (Architecture Skeleton) ---\n{skeleton}\n"
                
                if char_count + len(file_context) > MAX_CONTEXT_LENGTH:
                    context.append("\n[Warning: Workspace map truncated due to size limits]")
                    return "".join(context)
                    
                context.append(file_context)
                char_count += len(file_context)
    
    return "".join(context)