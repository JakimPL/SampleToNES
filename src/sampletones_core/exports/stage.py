from enum import StrEnum
from typing import Final, FrozenSet


class ExportStage(StrEnum):
    """The work an export run is in the middle of, as the progress it reports names it.

    A format writes its file the moment it is handed one, and a format carrying its own player
    reaches that point through two longer passes: the song is played out tick by tick, and the
    result is compressed to what the console has room for. Each stage counts in its own unit, so
    what a report means is read from the stage it names.

    A stage either travels toward what it is measured against or is merely measured against it.
    Walking arrives at the song's last tick and writing at its last file, so how far each has come
    is how far it has to go. Compressing ends when the song offers no further phrase that pays for
    itself, so its bytes are measured against the room the console has and reach it only by
    overflowing; :data:`TRAVELLING_STAGES` is what separates the two.
    """

    WALKING = "walking"
    COMPRESSING = "compressing"
    WRITING = "writing"


TRAVELLING_STAGES: Final[FrozenSet[ExportStage]] = frozenset(
    {
        ExportStage.WALKING,
        ExportStage.WRITING,
    }
)
