"""Initial migration

Revision ID: b6be144f57d1
Revises: 
Create Date: 2026-04-21 10:09:00.300808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6be144f57d1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS registry (
            id            TEXT PRIMARY KEY,
            manifest_json TEXT NOT NULL,
            app_url       TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id           TEXT PRIMARY KEY,
            email        TEXT NOT NULL UNIQUE,
            name         TEXT NOT NULL,
            provider     TEXT NOT NULL,
            provider_sub TEXT NOT NULL,
            created_at   DOUBLE PRECISION NOT NULL,
            updated_at   DOUBLE PRECISION NOT NULL,
            UNIQUE(provider, provider_sub)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id   SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id TEXT    NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY(user_id, role_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(role_id) REFERENCES roles(id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS apps (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            visibility TEXT NOT NULL DEFAULT 'internal',
            status     TEXT NOT NULL DEFAULT 'stable',
            created_at DOUBLE PRECISION NOT NULL,
            updated_at DOUBLE PRECISION NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app_permissions (
            id           SERIAL PRIMARY KEY,
            app_id       TEXT NOT NULL,
            subject_type TEXT NOT NULL,
            subject_id   TEXT NOT NULL,
            permission   TEXT NOT NULL,
            created_at   DOUBLE PRECISION NOT NULL,
            UNIQUE(app_id, subject_type, subject_id, permission)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id            SERIAL PRIMARY KEY,
            user_id       TEXT,
            action        TEXT NOT NULL,
            target_type   TEXT,
            target_id     TEXT,
            metadata_json TEXT NOT NULL,
            created_at    DOUBLE PRECISION NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            updated_at DOUBLE PRECISION NOT NULL,
            default_language      TEXT NOT NULL DEFAULT 'es',
            member_default_role   TEXT NOT NULL DEFAULT 'member',
            allowed_apps          TEXT,
            notification_defaults TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tenant_memberships (
            id        SERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id   TEXT NOT NULL,
            role      TEXT NOT NULL DEFAULT 'member',
            created_at DOUBLE PRECISION NOT NULL,
            UNIQUE(tenant_id, user_id),
            FOREIGN KEY(tenant_id) REFERENCES tenants(id),
            FOREIGN KEY(user_id)   REFERENCES users(id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS plugin_installs (
            id           SERIAL PRIMARY KEY,
            tenant_id    TEXT NOT NULL,
            plugin_id    TEXT NOT NULL,
            installed_at DOUBLE PRECISION NOT NULL,
            installed_by TEXT,
            status       TEXT NOT NULL DEFAULT 'active',
            UNIQUE(tenant_id, plugin_id),
            FOREIGN KEY(tenant_id) REFERENCES tenants(id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS plugins (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            icon        TEXT NOT NULL DEFAULT '📦',
            visibility  TEXT NOT NULL DEFAULT 'internal',
            created_at  DOUBLE PRECISION NOT NULL,
            updated_at  DOUBLE PRECISION NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS plugin_versions (
            id           SERIAL PRIMARY KEY,
            plugin_id    TEXT NOT NULL,
            version      TEXT NOT NULL DEFAULT '1.0.0',
            manifest_json TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'published',
            published_at DOUBLE PRECISION NOT NULL,
            created_at   DOUBLE PRECISION NOT NULL,
            UNIQUE(plugin_id, version),
            FOREIGN KEY(plugin_id) REFERENCES plugins(id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id             TEXT    PRIMARY KEY REFERENCES users(id),
            theme               TEXT    NOT NULL DEFAULT 'dark',
            language            TEXT    NOT NULL DEFAULT 'es',
            timezone            TEXT    NOT NULL DEFAULT 'UTC',
            reduced_motion      INTEGER NOT NULL DEFAULT 0,
            font_scale          REAL    NOT NULL DEFAULT 1.0,
            notification_email  INTEGER NOT NULL DEFAULT 1,
            notification_digest TEXT    NOT NULL DEFAULT 'weekly'
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id       TEXT    PRIMARY KEY REFERENCES users(id),
            avatar_url    TEXT,
            bio           TEXT,
            display_name  TEXT,
            show_activity INTEGER NOT NULL DEFAULT 1,
            show_email    INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_tenant_preferences (
            user_id          TEXT NOT NULL REFERENCES users(id),
            tenant_id        TEXT NOT NULL REFERENCES tenants(id),
            default_home_app TEXT,
            notify_app_ids   TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY (user_id, tenant_id)
        )
        """
    )
    op.execute(
        "INSERT INTO roles(name) VALUES ('owner'), ('admin'), ('member'), ('viewer') ON CONFLICT(name) DO NOTHING"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS user_tenant_preferences")
    op.execute("DROP TABLE IF EXISTS user_profiles")
    op.execute("DROP TABLE IF EXISTS user_preferences")
    op.execute("DROP TABLE IF EXISTS plugin_versions")
    op.execute("DROP TABLE IF EXISTS plugins")
    op.execute("DROP TABLE IF EXISTS plugin_installs")
    op.execute("DROP TABLE IF EXISTS tenant_memberships")
    op.execute("DROP TABLE IF EXISTS tenants")
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS app_permissions")
    op.execute("DROP TABLE IF EXISTS apps")
    op.execute("DROP TABLE IF EXISTS user_roles")
    op.execute("DROP TABLE IF EXISTS roles")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS registry")
