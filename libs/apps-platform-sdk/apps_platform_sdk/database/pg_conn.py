from __future__ import annotations

from typing import Callable


class PgConn:
    """psycopg2 connection wrapper with sqlite3-compatible interface: ? placeholders, context-manager commit/rollback, column-name row access."""

    def __init__(self, pg_conn) -> None:
        self._conn = pg_conn
        self._cur = pg_conn.cursor()

    def execute(self, sql: str, params: tuple = ()):
        self._cur.execute(sql.replace("?", "%s"), params)
        return self._cur

    def executemany(self, sql: str, seq_of_params):
        self._cur.executemany(sql.replace("?", "%s"), seq_of_params)
        return self._cur

    def set_tenant(self, tenant_id: str | None) -> None:
        """Set app.current_tenant on this session for RLS enforcement.

        Passing None or '' clears the restriction (all rows visible).
        This is intentional for system operations (migrations, bootstrap) that
        run outside a request context where no tenant is active.
        """
        self._cur.execute(
            "SELECT set_config('app.current_tenant', %s, FALSE)",
            (tenant_id or "",),
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()


def make_db_factory(database_url: str) -> Callable[[], PgConn]:
    """Return a zero-argument callable that opens and returns a new PgConn."""
    def _db() -> PgConn:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
        return PgConn(conn)
    return _db


def make_tenant_db_factory(
    database_url: str,
    tenant_id_fn: Callable[[], str | None],
) -> Callable[[], PgConn]:
    """Return a factory that opens a PgConn and sets app.current_tenant via RLS.

    tenant_id_fn is called on every connection open. When it returns None
    (e.g. during bootstrap or migrations outside a request context) the tenant
    is cleared and all rows remain accessible — which is the correct behaviour
    for system-level operations.
    """
    base = make_db_factory(database_url)

    def _db() -> PgConn:
        conn = base()
        conn.set_tenant(tenant_id_fn())
        return conn

    return _db
