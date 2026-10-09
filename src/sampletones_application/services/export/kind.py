from enum import Enum


class ExportKind(str, Enum):
    """The artifact one export run produced, naming the dialog that reports it."""

    WAV = "wav"
    INSTRUMENT = "instrument"
    SAMPLE = "sample"
    PROJECT = "project"
