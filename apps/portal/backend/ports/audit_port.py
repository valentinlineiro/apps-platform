from typing import Protocol


class AuditPort(Protocol):
    def log(
        self,
        user_id: str | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> None: ...

    def list_user_entries(self, user_id: str, limit: int) -> list[dict]: ...

    def list_all_entries(self, limit: int, offset: int = 0) -> list[dict]: ...
