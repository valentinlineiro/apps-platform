"""Initial exam corrector migration

Revision ID: ee9f1c2456e9
Revises: 
Create Date: 2026-04-21 10:34:57.454669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee9f1c2456e9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            status      TEXT NOT NULL,
            progress    INTEGER NOT NULL DEFAULT 0,
            stage       TEXT,
            message     TEXT,
            template_id TEXT,
            created_at  DOUBLE PRECISION NOT NULL,
            updated_at  DOUBLE PRECISION NOT NULL,
            finished_at DOUBLE PRECISION,
            result_json TEXT,
            error       TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS batches (
            id          TEXT PRIMARY KEY,
            template_id TEXT NOT NULL,
            total       INTEGER NOT NULL,
            done        INTEGER NOT NULL DEFAULT 0,
            failed      INTEGER NOT NULL DEFAULT 0,
            created_at  DOUBLE PRECISION NOT NULL,
            finished_at DOUBLE PRECISION
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_items (
            batch_id     TEXT NOT NULL,
            idx          INTEGER NOT NULL,
            filename     TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'queued',
            result_json  TEXT,
            error        TEXT,
            confidence   DOUBLE PRECISION,
            needs_review INTEGER NOT NULL DEFAULT 0,
            reviewed     INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (batch_id, idx)
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS batch_items")
    op.execute("DROP TABLE IF EXISTS batches")
    op.execute("DROP TABLE IF EXISTS jobs")
