from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class PaymentRetryScheduler(ABC):
    @abstractmethod
    def schedule_retry(
        self,
        retry_id: UUID,
        run_at: datetime,
    ) -> None:
        """Schedule processing of a retry at the specified time."""
        raise NotImplementedError

    @abstractmethod
    def enqueue_retry(self, retry_id: UUID) -> None:
        """Queue a retry for immediate processing."""
        raise NotImplementedError
