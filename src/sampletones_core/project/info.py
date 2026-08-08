from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.constants.project import (
    DEFAULT_PROJECT_AUTHOR,
    DEFAULT_PROJECT_COMMENT,
    DEFAULT_PROJECT_TITLE,
    MAX_PROJECT_AUTHOR_LENGTH,
    MAX_PROJECT_COMMENT_LENGTH,
    MAX_PROJECT_TITLE_LENGTH,
)


def now() -> datetime:
    return datetime.now(UTC)


class ProjectInfo(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    title: str = Field(
        default=DEFAULT_PROJECT_TITLE,
        max_length=MAX_PROJECT_TITLE_LENGTH,
        description="Human-readable project title.",
    )
    author: str = Field(
        default=DEFAULT_PROJECT_AUTHOR,
        max_length=MAX_PROJECT_AUTHOR_LENGTH,
        description="Project author.",
    )
    comment: str = Field(
        default=DEFAULT_PROJECT_COMMENT,
        max_length=MAX_PROJECT_COMMENT_LENGTH,
        description="Free-form project notes.",
    )
    created: datetime = Field(default_factory=now, description="Creation timestamp (UTC).")
    modified: datetime = Field(default_factory=now, description="Last modification timestamp (UTC).")

    def touch(self) -> None:
        self.modified = now()
