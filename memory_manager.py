"""
SQLite-backed persistent memory manager for MyAssistant.
Provides:
- Normalized user preference/fact storage
- Conversation history tracking with context window extraction
- Structured audit logging for action execution accountability
"""

import os
import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), "assistant_memory.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                target TEXT,
                status TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    _migrate_json_memories()


def normalize_key(key: str) -> str:
    """Normalize fact keys: lowercase, strip punctuation, replace spaces/hyphens with underscores."""
    k = key.strip().lower()
    k = re.sub(r"[^\w\s]", "", k)
    k = re.sub(r"[\s\-]+", "_", k)
    return k


def _migrate_json_memories():
    """Migrate legacy personal_memory.json facts into SQLite if not already present."""
    json_path = os.path.join(os.path.dirname(__file__), "personal_memory.json")
    if not os.path.exists(json_path):
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                with get_db() as conn:
                    for k, v in data.items():
                        norm_k = normalize_key(k)
                        # Avoid bogus migrations where key == value without meaning
                        if norm_k and v and norm_k != v.lower():
                            conn.execute(
                                "INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)",
                                (norm_k, str(v))
                            )
    except Exception:
        pass


def save_fact(key: str, value: str):
    """Save or update a personal fact/preference."""
    norm_k = normalize_key(key)
    if not norm_k or not value:
        return
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (norm_k, value.strip())
        )


def get_fact(key: str) -> str | None:
    """Retrieve a personal fact by key."""
    norm_k = normalize_key(key)
    with get_db() as conn:
        row = conn.execute("SELECT value FROM preferences WHERE key = ?", (norm_k,)).fetchone()
        return row["value"] if row else None


def get_all_facts() -> dict[str, str]:
    """Retrieve all stored personal facts as a dictionary."""
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM preferences ORDER BY key").fetchall()
        return {row["key"]: row["value"] for row in rows}


def add_conversation_turn(role: str, content: str):
    """Record a message in persistent conversation history."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversation (role, content) VALUES (?, ?)",
            (role, content)
        )


def get_recent_conversation(limit: int = 6) -> list[dict[str, str]]:
    """Retrieve the last N messages formatted for Ollama."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversation ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def log_action(action_type: str, target: str, status: str, details: str = ""):
    """Record an executed action in the structured security audit log."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO audit_log (action_type, target, status, details) VALUES (?, ?, ?, ?)",
            (action_type, target, status, details)
        )


def get_recent_audit_logs(limit: int = 10) -> list[dict]:
    """Retrieve recent security audit logs."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, action_type, target, status, details, timestamp FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# Auto-initialize database on import
init_db()
