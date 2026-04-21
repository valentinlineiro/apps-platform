"""Make registry.last_heartbeat nullable

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-21

Static apps registered via _init_static_apps() don't send heartbeats,
so last_heartbeat must be nullable for those rows.

"""
from alembic import op

revision = 'b3c4d5e6f7a8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE registry ALTER COLUMN last_heartbeat DROP NOT NULL")


def downgrade():
    op.execute("ALTER TABLE registry ALTER COLUMN last_heartbeat SET NOT NULL")
