from enum import StrEnum
from typing import Tuple

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


class HistoryDetailSegment(BaseModel, frozen=True):
    """One colored token of a history entry's detail line."""

    text: str
    role: HistoryDetailRole


HistoryDetail = Tuple[HistoryDetailSegment, ...]
