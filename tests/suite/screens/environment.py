import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Mapping, Tuple

from sampletones_shared.application import SAMPLETONES_ENV_PREFIX
from tests.suite.screens.dearpygui.display import DisplayBackend, ScreenSize
from tests.suite.screens.paths import ARTIFACTS_DIRECTORY, HOME_FOLDER, NO_BUS_FILE, REPORTS_FILE

DISPLAY_BACKEND_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_DISPLAY"
ARTIFACTS_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_ARTIFACTS"
REPORT_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_REPORT"
STRICT_HISTORY_VARIABLE: Final[str] = f"{SAMPLETONES_ENV_PREFIX}STRICT_HISTORY"
STRICT_HISTORY: Final[str] = "true"
NO_INPUT_METHOD: Final[str] = "@im=none"
DROPPED_PREFIXES: Final[Tuple[str, ...]] = ("PYTEST_", "WAYLAND_")
UNSAFE_CHARACTERS: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9_.-]+")
SCREEN_SIZE: Final[ScreenSize] = ScreenSize(width=1600, height=1000)
DEFAULT_DISPLAY_BACKEND: Final[DisplayBackend] = DisplayBackend.XVFB


def display_backend(environment: Mapping[str, str]) -> DisplayBackend:
    """The X server a run draws on: Xvfb unless ``SAMPLETONES_SCREENS_DISPLAY`` names another."""
    return DisplayBackend(environment.get(DISPLAY_BACKEND_VARIABLE, DEFAULT_DISPLAY_BACKEND))


@dataclass(frozen=True)
class ScenarioFolders:
    """Where one scenario's run keeps its files: the home its application lives in, and its reports.

    Attributes:
        root: The scenario's folder under the run's artifacts, kept after the run for a reader.
        home: The home directory the application reads and writes as the user's own.
        reports: The file the child process writes its pytest reports to.
    """

    root: Path
    home: Path
    reports: Path

    @classmethod
    def of(cls, nodeid: str) -> "ScenarioFolders":
        """The folders of the scenario ``nodeid`` names, under a name a file system accepts."""
        root = ARTIFACTS_DIRECTORY / UNSAFE_CHARACTERS.sub("_", nodeid)
        return cls(
            root=root,
            home=root / HOME_FOLDER,
            reports=root / REPORTS_FILE,
        )

    def prepare(self) -> None:
        """Clears what an earlier run of the scenario left, and lays out an empty home."""
        shutil.rmtree(self.root, ignore_errors=True)
        self.home.mkdir(parents=True)


def child_environment(
    base: Mapping[str, str],
    folders: ScenarioFolders,
    *,
    display: str,
) -> Dict[str, str]:
    """The environment a scenario's process starts under: ``base``, pointed at the scenario's own world.

    The home and every XDG directory lie inside the scenario's folder, so settings, session state
    and the documents folder start empty and stay apart from the user's. The display is the
    worker's own server, the session bus address leads nowhere, and the input method is off, so
    everything a scenario does stays on its own display and in its own home.
    """
    environment = {name: value for name, value in base.items() if not name.startswith(DROPPED_PREFIXES)}
    home = folders.home
    environment.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            "XDG_DOCUMENTS_DIR": str(home / "Documents"),
            "DISPLAY": display,
            "DBUS_SESSION_BUS_ADDRESS": f"unix:path={folders.root / NO_BUS_FILE}",
            "XMODIFIERS": NO_INPUT_METHOD,
            STRICT_HISTORY_VARIABLE: STRICT_HISTORY,
            ARTIFACTS_VARIABLE: str(folders.root),
            REPORT_VARIABLE: str(folders.reports),
        }
    )
    return environment
