from enum import StrEnum

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


class HistoryDetailSegment(BaseModel, frozen=True):
    """One coloured token of a history entry's detail line."""

    text: str
    role: HistoryDetailRole
