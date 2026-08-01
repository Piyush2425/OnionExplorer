"""
Deduplication & State Persistence Engine
"""

from abc import ABC, abstractmethod
import sqlite3
import os
from typing import Set, Optional, Dict
from ..models import ThreatActorLocation

class BaseStateStore(ABC):
    """Abstract interface for location deduplication store."""

    @abstractmethod
    def has_seen(self, location: ThreatActorLocation) -> bool:
        """Check if location key has been seen previously."""
        pass

    @abstractmethod
    def add(self, location: ThreatActorLocation) -> bool:
        """Record location. Returns True if new, False if already seen."""
        pass

    @abstractmethod
    def get_status(self, location: ThreatActorLocation) -> Optional[str]:
        """Get last recorded status for location."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Return total number of tracked location links."""
        pass

class MemoryStateStore(BaseStateStore):
    """Fast, in-memory deduplication store."""

    def __init__(self):
        self._keys: Set[str] = set()
        self._statuses: Dict[str, str] = {}

    def has_seen(self, location: ThreatActorLocation) -> bool:
        return location.unique_key in self._keys

    def add(self, location: ThreatActorLocation) -> bool:
        key = location.unique_key
        is_new = key not in self._keys
        self._keys.add(key)
        self._statuses[key] = location.status
        return is_new

    def get_status(self, location: ThreatActorLocation) -> Optional[str]:
        return self._statuses.get(location.unique_key)

    def size(self) -> int:
        return len(self._keys)

class SQLiteStateStore(BaseStateStore):
    """Persistent SQLite database deduplication store."""

    def __init__(self, db_path: str = "threat_locations_state.db"):
        self.db_path = os.path.abspath(db_path)
        self._init_db()

    def _execute(self, query: str, params: tuple = ()):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                cursor = conn.execute(query, params)
                return cursor.fetchall()
        finally:
            conn.close()

    def _init_db(self):
        self._execute("""
            CREATE TABLE IF NOT EXISTS location_cache (
                unique_key TEXT PRIMARY KEY,
                group_name TEXT,
                location_url TEXT,
                source_feed TEXT,
                status TEXT,
                first_seen TEXT,
                last_seen TEXT
            )
        """)

    def has_seen(self, location: ThreatActorLocation) -> bool:
        rows = self._execute("SELECT 1 FROM location_cache WHERE unique_key = ?", (location.unique_key,))
        return len(rows) > 0

    def add(self, location: ThreatActorLocation) -> bool:
        key = location.unique_key
        is_new = not self.has_seen(location)
        self._execute("""
            INSERT INTO location_cache (unique_key, group_name, location_url, source_feed, status, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(unique_key) DO UPDATE SET
                status = excluded.status,
                last_seen = excluded.last_seen
        """, (
            key,
            location.group_name,
            location.location_url,
            location.source_feed,
            location.status,
            location.discovered_at,
            location.discovered_at
        ))
        return is_new

    def get_status(self, location: ThreatActorLocation) -> Optional[str]:
        rows = self._execute("SELECT status FROM location_cache WHERE unique_key = ?", (location.unique_key,))
        return rows[0]["status"] if rows else None

    def size(self) -> int:
        rows = self._execute("SELECT COUNT(*) as cnt FROM location_cache")
        return rows[0]["cnt"] if rows else 0
