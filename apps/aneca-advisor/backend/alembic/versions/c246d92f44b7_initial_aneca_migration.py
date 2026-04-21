"""Initial aneca migration

Revision ID: c246d92f44b7
Revises: 
Create Date: 2026-04-21 10:12:30.424701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c246d92f44b7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aneca_journal_index (
            id       SERIAL PRIMARY KEY,
            issn_1   TEXT,
            issn_2   TEXT,
            quartile TEXT NOT NULL,
            title    TEXT,
            h_index  INTEGER,
            category TEXT
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aneca_journal_issn1 ON aneca_journal_index (issn_1)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aneca_journal_issn2 ON aneca_journal_index (issn_2)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aneca_articles (
            id           SERIAL PRIMARY KEY,
            user_id      TEXT NOT NULL,
            article_json TEXT NOT NULL,
            created_at   DOUBLE PRECISION NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_aneca_articles_user ON aneca_articles (user_id)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_aneca_articles_user")
    op.execute("DROP TABLE IF EXISTS aneca_articles")
    op.execute("DROP INDEX IF EXISTS idx_aneca_journal_issn2")
    op.execute("DROP INDEX IF EXISTS idx_aneca_journal_issn1")
    op.execute("DROP TABLE IF EXISTS aneca_journal_index")
