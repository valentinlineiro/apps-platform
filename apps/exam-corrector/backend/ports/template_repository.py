from abc import ABC, abstractmethod

from domain.template import SavedTemplate


class TemplateRepository(ABC):
    @abstractmethod
    def list(self) -> list[SavedTemplate]: ...

    @abstractmethod
    def get_path(self, template_id: str) -> str | None: ...

    @abstractmethod
    def save(self, source_path: str, name: str) -> SavedTemplate: ...

    @abstractmethod
    def delete(self, template_id: str) -> bool: ...

    @abstractmethod
    def get_bbox_cache(self, image_hash: str) -> dict | None: ...

    @abstractmethod
    def set_bbox_cache(self, image_hash: str, data: dict) -> None: ...
