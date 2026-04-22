from __future__ import annotations


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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()


def make_db_factory(database_url: str):
    """Return a zero-argument callable that opens and returns a new PgConn."""
    def _db() -> PgConn:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
        return PgConn(conn)
    return _db
