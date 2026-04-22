"""Drop unused apps and app_permissions tables

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-22

"""
from alembic import op

revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TABLE IF EXISTS app_permissions")
    op.execute("DROP TABLE IF EXISTS apps")


def downgrade():
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
