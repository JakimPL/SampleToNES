from enum import Enum


class ExportKind(str, Enum):
    """The artefact one export run produced, naming the dialog that reports it."""

    WAV = "wav"
    INSTRUMENT = "instrument"
    INSTRUMENTS = "instruments"
