import sqlite3
import os
import time

def init_checkpoint_db(db_path=".locdex_checkpoints.db"):
    """Initializes the SQLite database for local file state snapshots."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT,
            content TEXT,
            timestamp REAL
        )
    """)
    return conn

def save_checkpoint(filepath: str, db_path=".locdex_checkpoints.db"):
    """Saves a snapshot of the file's current content before modifying it."""
    if not os.path.exists(filepath):
        return  # If the file doesn't exist yet, there is no state to save.
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        conn = init_checkpoint_db(db_path)
        conn.execute(
            "INSERT INTO checkpoints (filepath, content, timestamp) VALUES (?, ?, ?)",
            (filepath, content, time.time())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[System] Warning: Could not save checkpoint for {filepath}. Error: {e}")

def restore_latest_checkpoint(filepath: str, db_path=".locdex_checkpoints.db") -> bool:
    """Restores the most recent checkpoint for a given file."""
    conn = init_checkpoint_db(db_path)
    # Fetch the most recent snapshot for this specific file
    row = conn.execute(
        "SELECT content FROM checkpoints WHERE filepath = ? ORDER BY timestamp DESC LIMIT 1", 
        (filepath,)
    ).fetchone()
    conn.close()
    
    if row:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(row[0])
            return True
        except Exception as e:
            print(f"[System] Error restoring checkpoint: {e}")
            return False
    return False