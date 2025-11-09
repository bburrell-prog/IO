#!/usr/bin/env python3
"""
Database module for storing screen analysis cycles.
Uses SQLite for local storage.
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class CycleDatabase:
    """Manages the SQLite database for analysis cycles."""

    def __init__(self, db_path: str = "cycles.db"):
        """Initialize the database connection and create tables if needed."""
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Create the cycles table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    screenshot_path TEXT,
                    report_path TEXT,
                    chatgpt_response TEXT,
                    statistics TEXT
                )
            """)
            conn.commit()

    def insert_cycle(self, timestamp: str, screenshot_path: Optional[str] = None,
                     report_path: Optional[str] = None, chatgpt_response: Optional[str] = None,
                     statistics: Optional[Dict[str, Any]] = None) -> int:
        """Insert a new cycle into the database. Returns the cycle ID."""
        stats_json = json.dumps(statistics) if statistics else None
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO cycles (timestamp, screenshot_path, report_path, chatgpt_response, statistics)
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, screenshot_path, report_path, chatgpt_response, stats_json))
            conn.commit()
            return cursor.lastrowid

    def get_all_cycles(self) -> List[Dict[str, Any]]:
        """Retrieve all cycles from the database."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM cycles ORDER BY id DESC").fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_cycle_by_id(self, cycle_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific cycle by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM cycles WHERE id = ?", (cycle_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def delete_cycle(self, cycle_id: int) -> bool:
        """Delete a cycle by ID. Returns True if deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cycles WHERE id = ?", (cycle_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert a database row to a dictionary."""
        cycle_id, timestamp, screenshot_path, report_path, chatgpt_response, statistics = row
        stats = json.loads(statistics) if statistics else None
        return {
            "id": cycle_id,
            "timestamp": timestamp,
            "screenshot_path": screenshot_path,
            "report_path": report_path,
            "chatgpt_response": chatgpt_response,
            "statistics": stats
        }