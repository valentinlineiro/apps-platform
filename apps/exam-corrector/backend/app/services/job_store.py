import json
import os
import sqlite3
import time

from domain.job import Job


class JobStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          TEXT PRIMARY KEY,
                    status      TEXT NOT NULL,
                    progress    INTEGER NOT NULL DEFAULT 0,
                    stage       TEXT,
                    message     TEXT,
                    template_id TEXT,
                    created_at  REAL NOT NULL,
                    updated_at  REAL NOT NULL,
                    finished_at REAL,
                    result_json TEXT,
                    error       TEXT
                )
            """)

    def create(self, job: Job) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO jobs
                   (id, status, progress, stage, message, template_id,
                    created_at, updated_at, finished_at, result_json, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job.id, job.status, job.progress, job.stage, job.message,
                    job.template_id, job.created_at, job.updated_at, job.finished_at,
                    json.dumps(job.result) if job.result is not None else None,
                    job.error,
                ),
            )

    def update(self, job_id: str, **fields) -> None:
        if not fields:
            return
        fields.setdefault("updated_at", time.time())
        if "result" in fields:
            result = fields.pop("result")
            fields["result_json"] = json.dumps(result) if result is not None else None
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [job_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)

    def get(self, job_id: str):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def delete_finished_before(self, cutoff: float) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM jobs WHERE status IN ('done', 'error') AND finished_at < ?",
                (cutoff,),
            )
            return cursor.rowcount

    @staticmethod
    def _row_to_job(row) -> Job:
        return Job(
            id=row["id"],
            status=row["status"],
            progress=row["progress"],
            stage=row["stage"] or "",
            message=row["message"] or "",
            template_id=row["template_id"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            finished_at=row["finished_at"],
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error=row["error"],
        )
