from enum import StrEnum
from typing import Tuple, Union

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
    FEATURE_VOLUME = "feature_volume"
    FEATURE_ARPEGGIO = "feature_arpeggio"
    FEATURE_PITCH = "feature_pitch"
    FEATURE_DUTY_CYCLE = "feature_duty_cycle"
    SEPARATOR = "separator"


class HistoryDetailWord(StrEnum):
    """A language-managed detail token, stored by key and translated at render time.

    Values mirror the ``SequencerHistoryElements`` members carrying the words, so
    a coordinator resolves a token exactly the way it resolves an entry's action
    label — committed entries stay language-independent.
    """

    LOOP_ON = "loop_on"
    LOOP_OFF = "loop_off"


class HistoryDetailSegment(BaseModel, frozen=True):
    """One coloured token of a history entry's detail line."""

    text: str
    role: HistoryDetailRole


class HistoryDetailWordSegment(BaseModel, frozen=True):
    """One coloured token whose text is looked up from the language manager when rendered."""

    word: HistoryDetailWord
    role: HistoryDetailRole


HistoryDetail = Tuple[Union[HistoryDetailSegment, HistoryDetailWordSegment], ...]
