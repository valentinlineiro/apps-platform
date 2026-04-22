"""Add indexes on hot-path columns

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-22

"""
from alembic import op

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE INDEX IF NOT EXISTS ix_plugin_installs_tenant_status ON plugin_installs (tenant_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tenant_memberships_user_id ON tenant_memberships (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_user_created ON audit_logs (user_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_plugin_installs_tenant_status")
    op.execute("DROP INDEX IF EXISTS ix_tenant_memberships_user_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_user_created")
    op.execute("DROP INDEX IF EXISTS ix_users_email")
