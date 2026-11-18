from sampletones_core.exports.format import ExportFormat
from sampletones_player.driver.image import DriverImage
from sampletones_player.export.program import Program
from sampletones_player.information import TextLine
from sampletones_player.nsf.file import nsf_to_bytes, song_room
from sampletones_player.nsf.header import HEADER_TEXT
from sampletones_player.song import Song
from sampletones_shared.paths.extensions import EXT_FILE_NSF


class NSFContainer:
    """Writes a program as an ``.nsf``, the file NES sound players and the console itself play.

    The file is a header naming the driver's routines, the driver, and the song behind it, so
    the song has the program area the driver leaves, and the program's text is listed in the
    header's three fields.
    """

    def __init__(self, driver: DriverImage) -> None:
        self._driver = driver

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.NSF

    @property
    def extension(self) -> str:
        return EXT_FILE_NSF

    @property
    def text(self) -> TextLine:
        return HEADER_TEXT

    @property
    def song_room(self) -> int:
        return song_room(self._driver)

    def to_bytes(self, song: Song, program: Program) -> bytes:
        return nsf_to_bytes(song, program.information, self._driver)
