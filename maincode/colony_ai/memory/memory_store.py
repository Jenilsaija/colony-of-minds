"""
Memory store persistence layer.
Implements SQLite tables for query interactions log, durable facts, and user preferences.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from colony.config import DEFAULT_MEMORY_DB_PATH

class MemoryStore:
    """
    Handles local long-term memory and history storage.
    Uses SQLite database engine to avoid external server dependencies.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get("COLONY_MEMORY_DB_PATH", DEFAULT_MEMORY_DB_PATH)
        self._init_db()

    def _init_db(self) -> None:
        """
        Creates necessary tables in the SQLite database if they do not exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Legacy log table for user interactions (kept for backward compatibility)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interaction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    routed_operators TEXT NOT NULL,
                    verified INTEGER NOT NULL
                )
            """)

            # New facts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    source TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    confidence REAL
                )
            """)

            # New preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL,
                    updated_at TEXT NOT NULL
                )
            """)

            # New interactions table (maps directly to specification)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_prompt TEXT NOT NULL,
                    selected_operators TEXT NOT NULL,
                    verified_facts TEXT NOT NULL,
                    final_answer TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def log_interaction(
        self, 
        query: str, 
        response: str, 
        routed_operators: List[str], 
        verified: bool,
        verified_facts: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Saves a record of an interaction in both legacy and new schema tables.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Write to legacy log for test suite checks
            cursor.execute(
                """
                INSERT INTO interaction_log (timestamp, query, response, routed_operators, verified)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, query, response, json.dumps(routed_operators), 1 if verified else 0)
            )

            # 2. Write to interactions table
            facts_json = json.dumps(verified_facts if verified_facts else [])
            cursor.execute(
                """
                INSERT INTO interactions (user_prompt, selected_operators, verified_facts, final_answer, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (query, json.dumps(routed_operators), facts_json, response, timestamp)
            )
            conn.commit()

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches the recent history of interactions from the legacy log (supporting tests).
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, query, response, routed_operators, verified FROM interaction_log ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            
            history = []
            for row in rows:
                history.append({
                    "timestamp": row["timestamp"],
                    "query": row["query"],
                    "response": row["response"],
                    "routed_operators": json.loads(row["routed_operators"]),
                    "verified": bool(row["verified"])
                })
            return history

    def store_fact(self, key: str, value: str, source: str = "user", confidence: float = 1.0) -> None:
        """Stores or replaces a fact in the database."""
        timestamp = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO facts (key, value, source, created_at, updated_at, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    source=excluded.source,
                    updated_at=excluded.updated_at,
                    confidence=excluded.confidence
                """,
                (key, value, source, timestamp, timestamp, confidence)
            )
            conn.commit()

    def get_fact(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a fact by its key."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, source, created_at, updated_at, confidence FROM facts WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def store_preference(self, name: str, value: str, confidence: float = 1.0) -> None:
        """Stores or replaces a preference in the database."""
        timestamp = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO preferences (name, value, confidence, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    value=excluded.value,
                    confidence=excluded.confidence,
                    updated_at=excluded.updated_at
                """,
                (name, value, confidence, timestamp)
            )
            conn.commit()

    def get_preference(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a preference by its name."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT name, value, confidence, updated_at FROM preferences WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def search_facts_and_preferences(self, term: str) -> List[Dict[str, Any]]:
        """Searches facts and preferences matching a search term."""
        results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Search facts
            cursor.execute(
                "SELECT 'fact' as type, key, value, confidence FROM facts WHERE key LIKE ? OR value LIKE ?",
                (f"%{term}%", f"%{term}%")
            )
            for row in cursor.fetchall():
                results.append(dict(row))
            # Search preferences
            cursor.execute(
                "SELECT 'preference' as type, name as key, value, confidence FROM preferences WHERE name LIKE ? OR value LIKE ?",
                (f"%{term}%", f"%{term}%")
            )
            for row in cursor.fetchall():
                results.append(dict(row))
        return results

