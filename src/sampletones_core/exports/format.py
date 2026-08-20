from enum import StrEnum


class ExportFormat(StrEnum):
    """A file format the application exports to, and the backend that writes it."""

    FAMITRACKER = "famitracker"
    BITPHASE = "bitphase"
    BITPHASE_PRESET = "bitphase_preset"
