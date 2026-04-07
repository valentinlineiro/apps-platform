from dataclasses import dataclass
from typing import Optional


@dataclass
class Job:
    id: str
    status: str          # queued | running | done | error
    progress: int
    stage: str
    message: str
    template_id: str
    created_at: float
    updated_at: float
    finished_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None
