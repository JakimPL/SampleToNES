from enum import StrEnum


class SourceKind(StrEnum):
    """The two kinds of row a converter's list holds.

    A recording stands for itself and a folder for what was found below it, which is what decides
    how a row is drawn, what one gesture on it settles, and what taking it out takes with it.
    """

    RECORDING = "recording"
    FOLDER = "folder"
