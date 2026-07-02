from typing import Tuple

from pydantic import BaseModel


class HistoryEntryViewModel(BaseModel, frozen=True):
    index: int
    label: str
    is_current: bool
    is_future: bool


class HistoryViewModel(BaseModel, frozen=True):
    entries: Tuple[HistoryEntryViewModel, ...]
    cursor: int

    @property
    def can_undo(self) -> bool:
        return self.cursor > 0

    @property
    def can_redo(self) -> bool:
        return self.cursor < len(self.entries) - 1

    @property
    def is_empty(self) -> bool:
        return not self.entries
