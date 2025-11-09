from enum import Enum
from typing import Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class TaskStatus(Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"


class TaskProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    completed: int
    current_item: Optional[str] = None

    def get_progress(self) -> float:
        if self.total == 0:
            return 0.0
        return self.completed / self.total
