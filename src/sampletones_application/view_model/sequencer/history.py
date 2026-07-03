from typing import Tuple

from pydantic import BaseModel

from sampletones_application.view_model.shared.history import HistoryDetailSegment


class HistoryEntryViewModel(BaseModel, frozen=True):
    index: int
    label: str
    detail_segments: Tuple[HistoryDetailSegment, ...]
    is_current: bool
    is_future: bool

    @property
    def has_detail(self) -> bool:
        return bool(self.detail_segments)


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
