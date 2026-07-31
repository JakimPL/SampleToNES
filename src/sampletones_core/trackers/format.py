from enum import StrEnum


class TrackerFormat(StrEnum):
    """A file format one tracker reads, and the backend that writes it."""

    FAMITRACKER = "famitracker"
    BITPHASE = "bitphase"
    BITPHASE_PRESET = "bitphase_preset"
