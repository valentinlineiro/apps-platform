from abc import ABC, abstractmethod


class BatchRepository(ABC):
    @abstractmethod
    def create_batch(self, batch_id: str, template_id: str, total: int) -> None: ...

    @abstractmethod
    def create_item(self, batch_id: str, idx: int, filename: str) -> None: ...

    @abstractmethod
    def update_item(self, batch_id: str, idx: int, **fields) -> None: ...

    @abstractmethod
    def finish_batch(self, batch_id: str) -> None: ...

    @abstractmethod
    def get_status(self, batch_id: str) -> dict | None: ...

    @abstractmethod
    def get_items(self, batch_id: str) -> list[dict]: ...

    @abstractmethod
    def get_review_items(self, batch_id: str) -> list[dict]: ...

    @abstractmethod
    def mark_reviewed(self, batch_id: str, idx: int) -> None: ...
