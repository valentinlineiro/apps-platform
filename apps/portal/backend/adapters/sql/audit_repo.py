import json
import time


class SqlAuditRepository:
    def __init__(self, db_factory):
        self._db = db_factory

    def log(
        self,
        user_id: str | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (user_id, action, target_type, target_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    json.dumps(metadata or {}, separators=(",", ":")),
                    time.time(),
                ),
            )

    def list_user_entries(self, user_id: str, limit: int) -> list[dict]:
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT id, action, target_type, target_id, created_at
                FROM audit_logs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "action": row["action"],
                "resource_type": row["target_type"],
                "resource_id": row["target_id"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
