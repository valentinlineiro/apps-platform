"""Enable Row-Level Security on tenant-scoped tables

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-22

RLS policies enforce tenant isolation as a second layer of defense.
When app.current_tenant is set on the connection, only rows belonging to
that tenant are visible/writable. When it is not set (migrations, system
bootstrap ops), all rows remain accessible.

NOTE: Without FORCE ROW LEVEL SECURITY the table owner bypasses RLS, which
means migrations and a superuser connection are always unrestricted. In
production, the application should connect as a non-owner role so that RLS
is enforced for all app traffic.
"""
from alembic import op

revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None

_TABLES = ('tenant_memberships', 'plugin_installs', 'user_tenant_preferences')

_POLICY_USING = """
    current_setting('app.current_tenant', TRUE) IS NULL
    OR current_setting('app.current_tenant', TRUE) = ''
    OR tenant_id = current_setting('app.current_tenant', TRUE)
"""


def upgrade():
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
                FOR ALL
                USING ({_POLICY_USING})
                WITH CHECK ({_POLICY_USING})
            """
        )


def downgrade():
    for table in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
