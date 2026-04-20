from abc import ABC, abstractmethod

from domain.job import Job


class JobRepository(ABC):
    @abstractmethod
    def create(self, job: Job) -> None: ...

    @abstractmethod
    def update(self, job_id: str, **fields) -> None: ...

    @abstractmethod
    def get(self, job_id: str) -> Job | None: ...

    @abstractmethod
    def delete_finished_before(self, cutoff: float) -> int: ...
