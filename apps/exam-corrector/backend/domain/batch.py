from dataclasses import dataclass, field
from enum import Enum


class BatchStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class ItemStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    ERROR = "error"


@dataclass
class BatchJob:
    id: str
    template_id: str
    total: int
    done: int = 0
    failed: int = 0
    needs_review: int = 0
    status: BatchStatus = BatchStatus.RUNNING
    created_at: float = 0.0
    finished_at: float | None = None


@dataclass
class BatchItem:
    batch_id: str
    idx: int
    filename: str
    status: ItemStatus = ItemStatus.PENDING
    confidence: float | None = None
    needs_review: bool = False
    reviewed: bool = False
    result: dict = field(default_factory=dict)
    error: str | None = None
