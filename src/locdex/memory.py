import sqlite3
import json
import time
from sentence_transformers import SentenceTransformer
import numpy as np
import os

# Initialize the lightweight local embedding model on load
# This will download the small ~90MB model on its first run
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def init_db(path="agent_memory.db"):
    """Initializes the SQLite database for local retrieval memory."""
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT,
            outcome TEXT,
            success INTEGER,
            embedding BLOB,
            timestamp REAL,
            access_count INTEGER DEFAULT 0
        )
    """)
    return conn

def save_memory(conn, task: str, outcome: str, success: bool):
    """Encodes the task and saves the outcome to the database."""
    emb = embedder.encode(task).astype(np.float32).tobytes()
    conn.execute(
        "INSERT INTO memory (task, outcome, success, embedding, timestamp) VALUES (?,?,?,?,?)",
        (task, outcome, int(success), emb, time.time())
    )
    conn.commit()

def recall_similar(conn, task: str, k: int = 3) -> list[str]:
    """Retrieves the top-k most similar past outcomes using cosine similarity and recency."""
    query_emb = embedder.encode(task).astype(np.float32)
    rows = conn.execute("SELECT id, task, outcome, embedding, timestamp, access_count FROM memory").fetchall()
    
    if not rows:
        return []
        
    scored = []
    for row in rows:
        stored_emb = np.frombuffer(row[3], dtype=np.float32)
        
        # Calculate Cosine Similarity
        similarity = np.dot(query_emb, stored_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(stored_emb))
        
        # Calculate Recency weight (decays over ~30 days)
        recency_weight = 1 / (1 + (time.time() - row[4]) / 86400 / 30)  
        
        # Blend scores
        score = (similarity * 0.7) + (recency_weight * 0.3)
        scored.append((score, row))
        
    # Sort by highest score descending
    scored.sort(key=lambda x: -x[0])
    top = scored[:k]
    
    # Update access counts for pruning later
    for _, row in top:
        conn.execute("UPDATE memory SET access_count = access_count + 1 WHERE id = ?", (row[0],))
    conn.commit()
    
    return [row[2] for _, row in top]