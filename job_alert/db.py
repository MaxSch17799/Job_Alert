from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .models import JobPosting
from .utils import DB_PATH, utc_now_iso


SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    site_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    last_adapter TEXT,
    resolved_url TEXT,
    last_status TEXT,
    last_success_at TEXT,
    last_failure_at TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS jobs_seen (
    site_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    PRIMARY KEY (site_id, job_id)
);

CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    site_id TEXT,
    status TEXT NOT NULL,
    message TEXT,
    new_jobs_count INTEGER NOT NULL DEFAULT 0,
    bootstrap INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts_sent (
    alert_key TEXT PRIMARY KEY,
    sent_at TEXT NOT NULL,
    category TEXT NOT NULL,
    site_id TEXT,
    payload_hash TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        self._init_db()

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def count_seen_jobs(self, site_id: str) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM jobs_seen WHERE site_id = ?", (site_id,)).fetchone()
            return int(row["total"])

    def has_seen_job(self, site_id: str, job_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT 1 FROM jobs_seen WHERE site_id = ? AND job_id = ?", (site_id, job_id)).fetchone()
            return row is not None

    def upsert_job(self, job: JobPosting) -> None:
        now = utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs_seen(site_id, job_id, title, url, first_seen_at, last_seen_at, raw_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(site_id, job_id) DO UPDATE SET
                    title = excluded.title,
                    url = excluded.url,
                    last_seen_at = excluded.last_seen_at,
                    raw_hash = excluded.raw_hash
                """,
                (job.site_id, job.job_id, job.title, job.url, now, now, job.raw_hash),
            )

    def update_site_status(
        self,
        site_id: str,
        label: str,
        *,
        adapter_name: str,
        resolved_url: str,
        success: bool,
        error_message: str = "",
    ) -> None:
        now = utc_now_iso()
        with self.connect() as conn:
            current = conn.execute("SELECT * FROM sites WHERE site_id = ?", (site_id,)).fetchone()
            failures = int(current["consecutive_failures"]) if current else 0
            if success:
                failures = 0
            else:
                failures += 1
            conn.execute(
                """
                INSERT INTO sites(site_id, label, last_adapter, resolved_url, last_status, last_success_at, last_failure_at, consecutive_failures, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(site_id) DO UPDATE SET
                    label = excluded.label,
                    last_adapter = excluded.last_adapter,
                    resolved_url = excluded.resolved_url,
                    last_status = excluded.last_status,
                    last_success_at = excluded.last_success_at,
                    last_failure_at = excluded.last_failure_at,
                    consecutive_failures = excluded.consecutive_failures,
                    last_error = excluded.last_error
                """,
                (
                    site_id,
                    label,
                    adapter_name,
                    resolved_url,
                    "success" if success else "failure",
                    now if success else (current["last_success_at"] if current else None),
                    now if not success else (current["last_failure_at"] if current else None),
                    failures,
                    error_message,
                ),
            )

    def get_site_status(self, site_id: str):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM sites WHERE site_id = ?", (site_id,)).fetchone()

    def log_run(self, site_id: str | None, status: str, message: str, *, new_jobs_count: int = 0, bootstrap: bool = False) -> None:
        now = utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runs(started_at, finished_at, site_id, status, message, new_jobs_count, bootstrap)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (now, now, site_id, status, message, new_jobs_count, 1 if bootstrap else 0),
            )

    def recent_runs(self, limit: int = 20):
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM runs ORDER BY run_id DESC LIMIT ?", (limit,)).fetchall())

    def should_send_alert(self, alert_key: str, payload: str) -> bool:
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        category, _, site_id = alert_key.partition("::")
        with self.connect() as conn:
            row = conn.execute("SELECT payload_hash FROM alerts_sent WHERE alert_key = ?", (alert_key,)).fetchone()
            if row and row["payload_hash"] == payload_hash:
                return False
            conn.execute(
                """
                INSERT INTO alerts_sent(alert_key, sent_at, category, site_id, payload_hash)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(alert_key) DO UPDATE SET
                    sent_at = excluded.sent_at,
                    payload_hash = excluded.payload_hash
                """,
                (alert_key, utc_now_iso(), category, site_id or None, payload_hash),
            )
        return True

