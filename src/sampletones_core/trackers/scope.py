from enum import StrEnum


class ExportScope(StrEnum):
    """How much of the application's work one export run carries.

    A backend decides how each scope materialises on disk, so a format that reads a
    whole reconstruction from a single file is free to write one.
    """

    INSTRUMENT = "instrument"
    SAMPLE = "sample"
    PROJECT = "project"


class DestinationKind(StrEnum):
    """Whether a scope's destination is a file to write or a directory to fill.

    The coordinator reads this to choose between a save-file and a select-directory
    dialog, so the choice follows the backend rather than a branch on format.
    """

    FILE = "file"
    DIRECTORY = "directory"
