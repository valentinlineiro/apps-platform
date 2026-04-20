from dataclasses import dataclass


@dataclass
class SavedTemplate:
    id: str
    name: str
    filename: str
    created_at: float
