from apps_platform_sdk import AuditLogger as _AuditLogger


class SqlAuditRepository(_AuditLogger):
    """Portal-specific audit repository backed by the shared SDK AuditLogger."""
