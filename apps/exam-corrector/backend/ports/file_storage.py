from abc import ABC, abstractmethod


class FileStorage(ABC):
    @abstractmethod
    def save_upload(self, file_obj, name: str) -> str:
        """Persist an uploaded file object and return its absolute path."""
        ...

    @abstractmethod
    def cleanup_old(self, max_age_seconds: int, protected: set[str]) -> None:
        """Delete temporary uploads older than max_age_seconds."""
        ...
