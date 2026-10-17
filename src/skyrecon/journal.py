"""Small append-only SQLite mission journal."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from time import time


class EventJournal:
    def __init__(self, path: str | Path = "skyrecon.db") -> None:
        self.path = str(path)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY, created REAL, kind TEXT, vehicle TEXT, payload TEXT)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record(self, kind: str, vehicle: str, **payload: object) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO events(created, kind, vehicle, payload) VALUES (?, ?, ?, ?)", (time(), kind, vehicle, json.dumps(payload, sort_keys=True)))

    def recent(self, limit: int = 100) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT sequence, created, kind, vehicle, payload FROM events ORDER BY sequence DESC LIMIT ?", (limit,)).fetchall()
        return [{"sequence": row[0], "created": row[1], "kind": row[2], "vehicle": row[3], "payload": json.loads(row[4])} for row in rows]
