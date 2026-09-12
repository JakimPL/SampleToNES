from enum import StrEnum


class SourceKind(StrEnum):
    """The two kinds of row a converter's list holds.

    A recording stands for itself and a folder for what was found below it, which is what decides
    how a row is drawn, what one gesture on it settles, and what taking it out takes with it.
    """

    RECORDING = "recording"
    FOLDER = "folder"


class SettingsField(StrEnum):
    """The per-recording choices a reader makes, by the name the settings hold each under.

    A further choice is one more member here, one more slot beside it, and one more line in the
    card that names them — which is what keeps a new field from reaching every layer by hand.
    """

    CHANNELS = "channels"
    BENDS = "bends"
