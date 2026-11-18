from typing import Protocol

from sampletones_core.exports.format import ExportFormat
from sampletones_player.export.program import Program
from sampletones_player.information import TextLine
from sampletones_player.song import Song


class ProgramContainer(Protocol):
    """The kind of file a program is written into.

    A program is the same song, driver and choices whichever file carries it, so everything that
    differs between the files lives here: the format the application offers it under, the
    extension its files take, the room each line of its text has, the room it leaves the song,
    and the bytes it lays the two out as.
    """

    @property
    def export_format(self) -> ExportFormat:
        """The format the application offers this kind of file under."""

    @property
    def extension(self) -> str:
        """The extension a file of this kind takes."""

    @property
    def text(self) -> TextLine:
        """The room each line of the program's text has in the file."""

    @property
    def song_room(self) -> int:
        """The bytes the file leaves the song block."""

    def to_bytes(self, song: Song, program: Program) -> bytes:
        """Builds the whole file playing ``song`` as ``program`` states it.

        Raises:
            SongTooLargeError: If the song takes more room than the file leaves it.
        """
