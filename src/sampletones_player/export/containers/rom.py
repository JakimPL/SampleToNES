from sampletones_core.exports.format import ExportFormat
from sampletones_player.driver.image import DriverImage
from sampletones_player.export.program import Program
from sampletones_player.information import ProgramText
from sampletones_player.rom.file import rom_to_bytes, song_room
from sampletones_player.rom.program import SCREEN_TEXT
from sampletones_player.shell.image import ShellImage
from sampletones_player.song import Song
from sampletones_shared.paths.extensions import EXT_FILE_ROM


class ROMContainer:
    """Writes a program as a ``.nes``, a cartridge image the console, emulators and flash cartridges run.

    The cartridge carries the driver and the song exactly as an NSF does, with the shell behind
    them: the code that starts the console, draws the player screen and answers the controller.
    The screen shows the program's text, so each line has the room its field on the screen gives it.
    """

    def __init__(self, driver: DriverImage, shell: ShellImage, patterns: bytes) -> None:
        self._driver = driver
        self._shell = shell
        self._patterns = patterns

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.ROM

    @property
    def extension(self) -> str:
        return EXT_FILE_ROM

    @property
    def text(self) -> ProgramText:
        return SCREEN_TEXT

    @property
    def song_room(self) -> int:
        return song_room(self._driver, self._shell)

    def to_bytes(self, song: Song, program: Program) -> bytes:
        return rom_to_bytes(song, program.information, self._driver, self._shell, self._patterns)
