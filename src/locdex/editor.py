import os

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules", "env"}
IGNORE_EXTS = {".pyc", ".db", ".sqlite3", ".exe", ".dll", ".so", ".zip", ".tar", ".gz"}

def get_workspace_context(repo_path: str = ".", max_chars: int = 12000) -> str:
    """
    Reads local files to provide workspace context to the LLM.
    Respects a maximum character limit to avoid blowing up the context window.
    """
    context_parts = []
    total_chars = 0
    
    for root, dirs, files in os.walk(repo_path):
        # Prune ignored directories in-place so os.walk skips them entirely
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in IGNORE_EXTS or file.startswith('.'):
                continue
                
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Skip empty files
                if not content.strip():
                    continue
                    
                file_header = f"\n--- File: {filepath} ---\n"
                
                # Stop appending if we hit our safe context limit
                if total_chars + len(content) + len(file_header) > max_chars:
                    break 
                    
                context_parts.append(file_header + content)
                total_chars += len(content) + len(file_header)
            except Exception:
                # Silently skip unreadable or binary files
                pass
                
    return "".join(context_parts)