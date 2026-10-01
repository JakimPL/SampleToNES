import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Self, Sequence, Tuple

from sampletones_shared.utils.system.programs import locate_program, missing_program_message
from sampletones_shared.utils.system.system import System
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.program.protocol import EXPORT_SWITCH

WINE: Final[str] = "wine"
WINE_PURPOSE: Final[str] = "FamiTracker is a Windows program, and Wine runs it on this system"
WINEPATH: Final[str] = "winepath"
WINDOWS_PATH_SWITCH: Final[str] = "-w"
WINE_DEBUG: Final[str] = "WINEDEBUG"
WINE_DEBUG_SILENT: Final[str] = "-all"
DISPLAY_VARIABLES: Final[Tuple[str, ...]] = ("DISPLAY", "WAYLAND_DISPLAY")
INSTALL_HINTS: Final[Dict[System, str]] = {
    System.LINUX: "sudo apt install wine",
    System.MACOS: "brew install --cask wine-stable",
}


@dataclass(frozen=True)
class WineProgram:
    """FamiTracker run through Wine, the way Linux and macOS run a Windows program.

    FamiTracker reads an argument starting with ``/`` as a switch, so a path reaches it as the
    Windows path Wine maps it to, which Wine's own ``winepath`` gives. The export shows no window,
    so it runs with no display and with Wine's diagnostics silenced, and a run leaves the desktop
    as it was.

    Attributes:
        wine: The wine program.
        executable: The FamiTracker program file.
    """

    wine: Path
    executable: Path

    @classmethod
    def located(cls, executable: Path) -> Self:
        """FamiTracker at ``executable``, run by the Wine this system has.

        Args:
            executable: The FamiTracker program file.

        Returns:
            Self: The program.

        Raises:
            FamiTrackerError: If Wine is absent, naming how this system installs it.
        """
        wine = locate_program(WINE)
        if wine is None:
            raise FamiTrackerError(missing_program_message(WINE, WINE_PURPOSE, INSTALL_HINTS))

        return cls(wine=wine, executable=executable)

    def export_command(
        self,
        module: Path,
        nsf: Path,
        log: Path,
    ) -> List[str]:
        """The command that exports a module to an NSF and writes FamiTracker's log, each path as Wine maps it.

        Args:
            module: The `.ftm` module to export.
            nsf: Where the NSF is written.
            log: Where FamiTracker writes what it did.

        Returns:
            List[str]: The program and its arguments.

        Raises:
            FamiTrackerError: If Wine fails to map the paths.
        """
        windows_module, windows_nsf, windows_log = self.windows_paths((module, nsf, log))
        return [
            str(self.wine),
            str(self.executable),
            windows_module,
            EXPORT_SWITCH,
            windows_nsf,
            windows_log,
        ]

    def windows_paths(self, paths: Sequence[Path]) -> Tuple[str, ...]:
        """The Windows path Wine maps each path to, asked of Wine in one call.

        Args:
            paths: The paths, absolute or relative to the working directory.

        Returns:
            Tuple[str, ...]: One Windows path per path, in the same order.

        Raises:
            FamiTrackerError: If Wine fails to map them.
        """
        try:
            completed = subprocess.run(
                [str(self.wine), WINEPATH, WINDOWS_PATH_SWITCH, *(str(path.resolve()) for path in paths)],
                env=self.environment(),
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise FamiTrackerError(f"Wine failed to map the paths it hands FamiTracker:\n{error.stderr}") from error

        mapped = tuple(completed.stdout.splitlines())
        if len(mapped) != len(paths):
            raise FamiTrackerError(f"Wine mapped {len(paths)} paths to {len(mapped)}: {completed.stdout!r}")

        return mapped

    def environment(self) -> Dict[str, str]:
        """The environment the export runs in: the check's own, with no display and Wine's diagnostics silenced."""
        environment = {name: value for name, value in os.environ.items() if name not in DISPLAY_VARIABLES}
        environment[WINE_DEBUG] = WINE_DEBUG_SILENT
        return environment
