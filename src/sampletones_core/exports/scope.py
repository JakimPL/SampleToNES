from enum import StrEnum


class ExportScope(StrEnum):
    """How much of the application's work one export run carries.

    A backend decides how each scope materialises on disk, so a format that reads a
    whole reconstruction from a single file is free to write one.
    """

    INSTRUMENT = "instrument"
    SAMPLE = "sample"
    PROJECT = "project"
