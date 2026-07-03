from enum import StrEnum
from typing import Tuple

from pydantic import BaseModel


class HistoryDetailRole(StrEnum):
    """The kind of data a detail segment carries, driving its colour.

    A role is a semantic tag chosen by the logic layer; the panel maps it to a
    concrete colour, keeping the detail-producing code free of any visual
    concern.
    """

    FRAME = "frame"
    CHANNEL = "channel"
    ROW = "row"
    INSTRUMENT = "instrument"
    TRANSPOSE = "transpose"
    VOLUME = "volume"
    VALUE = "value"
    SAMPLE = "sample"
    NAME = "name"
    FEATURE = "feature"
    SEPARATOR = "separator"


class HistoryDetailSegment(BaseModel, frozen=True):
    """One coloured token of a history entry's detail line."""

    text: str
    role: HistoryDetailRole


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
