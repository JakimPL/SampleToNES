from datetime import datetime
from typing import Final

from pydantic import BaseModel

_TIMESTAMP_FORMAT: Final[str] = "%Y-%m-%d %H:%M"


class ProjectPropertiesViewModel(BaseModel, frozen=True):
    """The project info the properties dialog renders and offers for editing."""

    title: str
    author: str
    comment: str
    created: datetime
    modified: datetime

    @property
    def created_text(self) -> str:
        return self.created.strftime(_TIMESTAMP_FORMAT)

    @property
    def modified_text(self) -> str:
        return self.modified.strftime(_TIMESTAMP_FORMAT)
