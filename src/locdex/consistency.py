import subprocess

def find_usages(symbol: str, repo_path: str, language: str) -> list[str]:
    """Finds files that reference a specific symbol using grep."""
    extensions = {
        "python": "*.py",
        "typescript": "*.ts,*.tsx,*.js,*.jsx",
        "go": "*.go",
    }
    include = extensions.get(language, "*")
    
    # Run grep recursively to find files containing the symbol
    try:
        result = subprocess.run(
            ["grep", "-rl", symbol, repo_path, f"--include={include}"],
            capture_output=True, text=True
        )
        return result.stdout.strip().split("\n") if result.stdout else []
    except Exception:
        # If grep fails (e.g., not installed on Windows without WSL), return empty
        return []

def check_consistency(changed_symbols: list[str], repo_path: str, language: str) -> dict:
    """
    v0.1: grep-based for all three languages — real but approximate.
    Flags any files that reference a symbol that was changed by the AI.
    """
    flagged = {}
    for symbol in changed_symbols:
        files = find_usages(symbol, repo_path, language)
        # If the symbol is found in more than one file, it's a consistency risk
        if len(files) > 1:
            flagged[symbol] = files
    return flagged