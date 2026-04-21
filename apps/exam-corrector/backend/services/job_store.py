import json
import time

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

from domain.job import Job


class JobStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        conn = psycopg2.connect(self.database_url, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn

    def create(self, job: Job) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO jobs
                       (id, status, progress, stage, message, template_id,
                        created_at, updated_at, finished_at, result_json, error)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
        
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [job_id]
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE jobs SET {set_clause} WHERE id = %s", values)

    def get(self, job_id: str):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
                row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def delete_finished_before(self, cutoff: float) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM jobs WHERE status IN ('done', 'error') AND finished_at < %s",
                    (cutoff,),
                )
                return cur.rowcount

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
