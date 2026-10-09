from enum import StrEnum


class SourceKind(StrEnum):
    """The kinds of row a stems list holds.

    A recording stands for itself and a folder for what was found below it, which is what decides
    how a row is drawn, what one gesture on it settles, and what taking it out takes with it. A
    list describing a finished conversion holds a third: the frames the reader wrote by hand,
    which answer to no recording and are named where they are drawn.
    """

    RECORDING = "recording"
    FOLDER = "folder"
    EDITS = "edits"


class SettingsField(StrEnum):
    """The per-recording choices a reader makes, by the name the settings hold each under.

    A further choice is one more member here, one more slot beside it, and one more line in the
    card that names them — which is what keeps a new field from reaching every layer by hand.
    """

    CHANNELS = "channels"
    BENDS = "bends"
