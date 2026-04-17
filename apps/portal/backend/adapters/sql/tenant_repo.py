import json
import time

from domain.tenant import Membership, Tenant


class SqlTenantRepository:
    def __init__(self, db_factory):
        self._db = db_factory

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        with self._db() as conn:
            row = conn.execute(
                "SELECT * FROM tenants WHERE id = ?", (tenant_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_tenant(row)

    def get_caller_role(self, tenant_id: str, user_id: str) -> str | None:
        with self._db() as conn:
            row = conn.execute(
                "SELECT role FROM tenant_memberships WHERE tenant_id = ? AND user_id = ?",
                (tenant_id, user_id),
            ).fetchone()
        return row["role"] if row else None

    def save_settings(self, tenant_id: str, updates: dict) -> Tenant | None:
        if not updates:
            return self.get_tenant(tenant_id)

        serialized = dict(updates)
        if "allowed_apps" in serialized:
            val = serialized["allowed_apps"]
            serialized["allowed_apps"] = json.dumps(val) if val is not None else None
        if "notification_defaults" in serialized:
            val = serialized["notification_defaults"]
            serialized["notification_defaults"] = json.dumps(val or {})

        serialized["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in serialized)
        with self._db() as conn:
            conn.execute(
                f"UPDATE tenants SET {set_clause} WHERE id = ?",
                (*serialized.values(), tenant_id),
            )
        return self.get_tenant(tenant_id)

    def list_members(self, tenant_id: str) -> list[Membership]:
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT u.id, u.email, u.name, tm.role, tm.created_at
                FROM tenant_memberships tm
                JOIN users u ON u.id = tm.user_id
                WHERE tm.tenant_id = ?
                ORDER BY tm.created_at
                """,
                (tenant_id,),
            ).fetchall()
        return [
            Membership(
                user_id=r["id"],
                email=r["email"],
                name=r["name"],
                role=r["role"],
                joined_at=r["created_at"],
            )
            for r in rows
        ]

    def find_user_by_email(self, email: str) -> str | None:
        with self._db() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
        return row["id"] if row else None

    def upsert_member(self, tenant_id: str, user_id: str, role: str) -> None:
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tenant_id, user_id) DO UPDATE SET role = excluded.role
                """,
                (tenant_id, user_id, role, time.time()),
            )

    def remove_member(self, tenant_id: str, user_id: str) -> None:
        with self._db() as conn:
            conn.execute(
                "DELETE FROM tenant_memberships WHERE tenant_id = ? AND user_id = ?",
                (tenant_id, user_id),
            )

    def get_membership_with_tenant(self, user_id: str) -> dict | None:
        with self._db() as conn:
            row = conn.execute(
                """
                SELECT t.id, t.name, tm.role
                FROM tenant_memberships tm
                JOIN tenants t ON t.id = tm.tenant_id
                WHERE tm.user_id = ?
                ORDER BY t.id
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "name": row["name"], "role": row["role"]}

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_tenant(row) -> Tenant:
        keys = row.keys() if hasattr(row, "keys") else row.keys()
        return Tenant(
            id=row["id"],
            name=row["name"],
            default_language=row["default_language"] if "default_language" in keys else "es",
            member_default_role=row["member_default_role"] if "member_default_role" in keys else "member",
            allowed_apps=(
                json.loads(row["allowed_apps"])
                if "allowed_apps" in keys and row["allowed_apps"]
                else None
            ),
            notification_defaults=(
                json.loads(row["notification_defaults"])
                if "notification_defaults" in keys and row["notification_defaults"]
                else {}
            ),
        )
