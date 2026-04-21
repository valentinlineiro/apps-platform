"""Add app_url column to registry

Revision ID: a1b2c3d4e5f6
Revises: b6be144f57d1
Create Date: 2026-04-21

"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'b6be144f57d1'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE registry ADD COLUMN IF NOT EXISTS app_url TEXT")


def downgrade():
    op.execute("ALTER TABLE registry DROP COLUMN IF EXISTS app_url")
