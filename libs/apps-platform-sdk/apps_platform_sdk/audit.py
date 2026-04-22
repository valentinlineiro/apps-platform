"""Centralized audit logging primitives shared across all platform backends.

AuditActions  — canonical action-string constants (prevents typos, enables grep).
AuditLogger   — db-backed logger that writes to the shared `audit_logs` table.
"""
from __future__ import annotations

import json
import time


class AuditActions:
    """Standard platform-wide audit action strings.

    Grouped by category so callers can import and grep by prefix.
    Stored as-is in the DB — do not rename without a migration.
    """

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"

    # Tenant administration
    TENANT_SETTINGS_UPDATED = "tenant_settings_updated"
    TENANT_MEMBER_ADDED = "tenant_member_added"
    TENANT_MEMBER_REMOVED = "tenant_member_removed"

    # Plugin / app catalog
    PLUGIN_INSTALLED = "plugin_installed"
    PLUGIN_UNINSTALLED = "plugin_uninstalled"
    PLUGIN_STATUS_UPDATED = "plugin_install_updated"


class AuditLogger:
    """Write and query audit events in the shared ``audit_logs`` table.

    Accepts a *db_factory* callable (returns a context-manager ``PgConn``) so
    it integrates with both ``make_db_factory`` and ``make_tenant_db_factory``.

    The ``audit_logs`` table schema (created by the portal's initial migration):
        id            SERIAL PRIMARY KEY
        user_id       TEXT
        action        TEXT NOT NULL
        target_type   TEXT
        target_id     TEXT
        metadata_json TEXT NOT NULL
        created_at    DOUBLE PRECISION NOT NULL
    """

    def __init__(self, db_factory) -> None:
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
                INSERT INTO audit_logs
                    (user_id, action, target_type, target_id, metadata_json, created_at)
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
        """Return the most recent *limit* events for a single user."""
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

    def list_all_entries(self, limit: int, offset: int = 0) -> list[dict]:
        """Return *limit* most recent events across all users (admin view).

        Joins with ``users`` so the caller gets human-readable identity.
        """
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT al.id, al.user_id, u.email, u.name,
                       al.action, al.target_type, al.target_id,
                       al.metadata_json, al.created_at
                FROM audit_logs al
                LEFT JOIN users u ON u.id = al.user_id
                ORDER BY al.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "user_email": row["email"],
                "user_name": row["name"],
                "action": row["action"],
                "resource_type": row["target_type"],
                "resource_id": row["target_id"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
