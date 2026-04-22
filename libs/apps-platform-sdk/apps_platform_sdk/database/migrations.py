from __future__ import annotations

import logging as _logging


def run_alembic_upgrade(database_url: str, alembic_ini: str, logger=None) -> None:
    """Run `alembic upgrade head` against *database_url* using the given ini file."""
    log = logger or _logging.getLogger(__name__)
    if not database_url:
        log.warning("DATABASE_URL not set, skipping migrations")
        return
    log.info("running database migrations (alembic)")
    try:
        import alembic.config
        import alembic.command
        cfg = alembic.config.Config(alembic_ini)
        alembic.command.upgrade(cfg, "head")
        log.info("database migrations complete")
    except Exception:
        log.error("database migrations failed", exc_info=True)
