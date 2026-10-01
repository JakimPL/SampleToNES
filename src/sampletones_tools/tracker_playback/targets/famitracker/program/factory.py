from pathlib import Path

from sampletones_shared.paths.extensions import EXT_FILE_WINDOWS_PROGRAM
from sampletones_shared.utils.system.system import System
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.program.native import NativeProgram
from sampletones_tools.tracker_playback.targets.famitracker.program.protocol import FamiTrackerProgram
from sampletones_tools.tracker_playback.targets.famitracker.program.wine import WineProgram


def located_program(executable: Path) -> FamiTrackerProgram:
    """FamiTracker at ``executable``, run the way this system runs a Windows program.

    Windows runs it directly, and Linux and macOS run it through Wine.

    Args:
        executable: The FamiTracker program file, ``FamiTracker.exe``.

    Returns:
        FamiTrackerProgram: The program.

    Raises:
        FamiTrackerError: If ``executable`` is no Windows program file, or Wine is absent where it is needed.
        OSError: If the system is unsupported.
    """
    if not executable.is_file() or executable.suffix.lower() != EXT_FILE_WINDOWS_PROGRAM:
        raise FamiTrackerError(f"{executable} is no Windows program file. Give the path to FamiTracker.exe itself.")

    match System.current():
        case System.WINDOWS:
            return NativeProgram(executable=executable)
        case System.LINUX | System.MACOS:
            return WineProgram.located(executable)
