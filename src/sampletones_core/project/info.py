from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.constants.application import SAMPLETONES_AUTHOR
from sampletones_shared.constants.project import (
    DEFAULT_PROJECT_COMMENT,
    DEFAULT_PROJECT_TITLE,
)


def now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectInfo(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    title: str = Field(default=DEFAULT_PROJECT_TITLE, description="Human-readable project title.")
    author: str = Field(default=SAMPLETONES_AUTHOR, description="Project author.")
    comment: str = Field(default=DEFAULT_PROJECT_COMMENT, description="Free-form project notes.")
    created: datetime = Field(default_factory=now, description="Creation timestamp (UTC).")
    modified: datetime = Field(default_factory=now, description="Last modification timestamp (UTC).")

    def touch(self) -> None:
        self.modified = now()
