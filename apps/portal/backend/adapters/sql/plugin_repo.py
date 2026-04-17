import json
import time

from domain.plugin import CatalogEntry, PluginInstall


class SqlPluginRepository:
    def __init__(self, db_factory, heartbeat_ttl: int = 60):
        self._db = db_factory
        self._heartbeat_ttl = heartbeat_ttl

    def list_installs(self, tenant_id: str) -> list[PluginInstall]:
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT pi.plugin_id, pi.status, pi.installed_at, pi.installed_by,
                       r.manifest_json, r.last_heartbeat
                FROM plugin_installs pi
                LEFT JOIN registry r ON r.id = pi.plugin_id
                WHERE pi.tenant_id = ?
                ORDER BY pi.installed_at
                """,
                (tenant_id,),
            ).fetchall()
        cutoff = time.time() - self._heartbeat_ttl
        return [
            PluginInstall(
                plugin_id=row["plugin_id"],
                status=row["status"],
                installed_at=row["installed_at"],
                installed_by=row["installed_by"],
                alive=(
                    row["last_heartbeat"] is not None
                    and row["last_heartbeat"] >= cutoff
                ),
                manifest=json.loads(row["manifest_json"]) if row["manifest_json"] else {},
            )
            for row in rows
        ]

    def install(self, tenant_id: str, plugin_id: str, installed_by: str | None) -> None:
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO plugin_installs (tenant_id, plugin_id, installed_at, installed_by, status)
                VALUES (?, ?, ?, ?, 'active')
                ON CONFLICT(tenant_id, plugin_id) DO NOTHING
                """,
                (tenant_id, plugin_id, time.time(), installed_by),
            )

    def update_status(self, tenant_id: str, plugin_id: str, status: str) -> bool:
        with self._db() as conn:
            result = conn.execute(
                "UPDATE plugin_installs SET status = ? WHERE tenant_id = ? AND plugin_id = ?",
                (status, tenant_id, plugin_id),
            )
        return result.rowcount > 0

    def uninstall(self, tenant_id: str, plugin_id: str) -> None:
        with self._db() as conn:
            conn.execute(
                "DELETE FROM plugin_installs WHERE tenant_id = ? AND plugin_id = ?",
                (tenant_id, plugin_id),
            )

    def get_catalog(self, tenant_id: str) -> list[CatalogEntry]:
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.name, p.description, p.icon, p.visibility,
                       pv.version, pv.manifest_json,
                       pi.status AS install_status
                FROM plugins p
                JOIN plugin_versions pv ON pv.plugin_id = p.id AND pv.status = 'published'
                LEFT JOIN plugin_installs pi ON pi.plugin_id = p.id AND pi.tenant_id = ?
                ORDER BY p.name
                """,
                (tenant_id,),
            ).fetchall()
        return [
            CatalogEntry(
                plugin_id=row["id"],
                name=row["name"],
                description=row["description"],
                icon=row["icon"],
                version=row["version"],
                installed=row["install_status"] is not None,
                install_status=row["install_status"],
                manifest={
                    **json.loads(row["manifest_json"]),
                    "visibility": row["visibility"],
                },
            )
            for row in rows
        ]

    def plugin_registered(self, plugin_id: str) -> bool:
        with self._db() as conn:
            row = conn.execute(
                "SELECT id FROM registry WHERE id = ?", (plugin_id,)
            ).fetchone()
        return row is not None
