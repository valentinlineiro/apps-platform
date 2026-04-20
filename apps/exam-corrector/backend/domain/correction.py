from dataclasses import dataclass, field
from enum import Enum


class MarkState(str, Enum):
    BLANK = "blank"
    SELECTED = "selected"
    CANCELLED = "cancelled"
    UNCERTAIN = "uncertain"


@dataclass
class AnswerFeedback:
    question: int
    correct: str
    given: str | None
    confidence: float
    mark_state: MarkState
    rule_applied: str | None = None


@dataclass
class CorrectionResult:
    feedback: list[AnswerFeedback] = field(default_factory=list)
    correct_count: int = 0
    total: int = 0
    score: float = 0.0
    max_score: float = 0.0
    min_confidence: float = 1.0
    needs_review: bool = False
