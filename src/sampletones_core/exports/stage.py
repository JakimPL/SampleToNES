from enum import StrEnum


class ExportStage(StrEnum):
    """The work an export run is in the middle of, as the progress it reports names it.

    A format writes its file the moment it is handed one, and a format carrying its own player
    reaches that point through two longer passes: the song is played out tick by tick, and the
    result is compressed to what the console has room for. Each stage counts in its own unit, so
    what a report means is read from the stage it names.
    """

    WALKING = "walking"
    COMPRESSING = "compressing"
    WRITING = "writing"
