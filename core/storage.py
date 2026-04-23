from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from .models import AlertEvent


class AlertStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS alarm_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    track_id INTEGER NOT NULL,
                    score REAL NOT NULL,
                    message TEXT NOT NULL,
                    frame_index INTEGER NOT NULL,
                    ts_ms INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.commit()

    def add_events(self, events: List[AlertEvent]):
        if not events:
            return
        rows = [
            (e.event_type, e.track_id, e.score, e.message, e.frame_index, e.ts_ms)
            for e in events
        ]
        with self._conn() as c:
            c.executemany(
                """
                INSERT INTO alarm_event(event_type, track_id, score, message, frame_index, ts_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            c.commit()

    def list_events(self, limit: int = 100, event_type: Optional[str] = None) -> List[Dict]:
        sql = "SELECT id, event_type, track_id, score, message, frame_index, ts_ms, created_at FROM alarm_event"
        args = []
        if event_type:
            sql += " WHERE event_type = ?"
            args.append(event_type)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)

        with self._conn() as c:
            cur = c.execute(sql, args)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        return rows

    def get_summary(self) -> Dict:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM alarm_event").fetchone()[0]
            max_id = c.execute("SELECT COALESCE(MAX(id), 0) FROM alarm_event").fetchone()[0]
            latest_created = c.execute(
                "SELECT created_at FROM alarm_event ORDER BY id DESC LIMIT 1"
            ).fetchone()
            by_type_rows = c.execute(
                """
                SELECT event_type, COUNT(*)
                FROM alarm_event
                GROUP BY event_type
                ORDER BY COUNT(*) DESC
                """
            ).fetchall()
            trend_rows = c.execute(
                """
                SELECT strftime('%Y-%m-%d %H:00', created_at) AS bucket, COUNT(*)
                FROM alarm_event
                GROUP BY bucket
                ORDER BY bucket DESC
                LIMIT 12
                """
            ).fetchall()

        by_type = {event_type: count for event_type, count in by_type_rows}
        trend = [
            {"bucket": bucket, "count": count}
            for bucket, count in reversed(trend_rows)
        ]
        return {
            "total_events": total,
            "latest_event_id": max_id,
            "latest_created_at": latest_created[0] if latest_created else None,
            "by_type": by_type,
            "trend": trend,
        }
