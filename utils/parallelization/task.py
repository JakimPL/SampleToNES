from typing import Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class TaskProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    completed: int
    current_item: Optional[str] = None
