from enum import StrEnum
from typing import Tuple, Union

from pydantic import BaseModel


class HistoryDetailRole(StrEnum):
    """The kind of data a detail segment carries, driving its color.

    A role is a semantic tag chosen by the logic layer; the panel maps it to a
    concrete color, keeping the detail-producing code free of any visual
    concern. Three of them read a voice: ``SAMPLE`` and ``INSTRUMENT`` name the
    kind a line is about, so its position and its name wear that kind's color,
    and ``VOICE`` carries a voice reference the kind says nothing about — the
    tracker's voice slot, and a voice the pool has stopped holding.
    """

    FRAME = "frame"
    CHANNEL = "channel"
    ROW = "row"
    VOICE = "voice"
    TRANSPOSE = "transpose"
    VOLUME = "volume"
    VALUE = "value"
    SAMPLE = "sample"
    INSTRUMENT = "instrument"
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
    """One colored token of a history entry's detail line."""

    text: str
    role: HistoryDetailRole


class HistoryDetailWordSegment(BaseModel, frozen=True):
    """One colored token whose text is looked up from the language manager when rendered."""

    word: HistoryDetailWord
    role: HistoryDetailRole


HistoryDetail = Tuple[Union[HistoryDetailSegment, HistoryDetailWordSegment], ...]
