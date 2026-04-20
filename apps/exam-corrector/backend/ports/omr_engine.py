from abc import ABC, abstractmethod


class OmrEngine(ABC):
    @abstractmethod
    def detect_bboxes(self, template_path: str) -> dict:
        """Analyse a template image and return per-option bounding boxes."""
        ...

    @abstractmethod
    def correct(
        self,
        template_path: str,
        exam_path: str,
        bbox_data: dict,
    ) -> dict | None:
        """Return per-answer mark data, or None when alignment fails."""
        ...
