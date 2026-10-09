from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Mapping, Tuple

from automation.dearpygui.display import DisplayBackend, ScreenSize
from automation.homes import let_go, reopen_folders
from automation.paths import (
    HOME_COPY_NOTE,
    HOME_FOLDER,
    KEPT_DIRECTORY,
    NO_BUS_FILE,
    REPORTS_FILE,
)
from sampletones_shared.application import SAMPLETONES_ENV_PREFIX

DISPLAY_BACKEND_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_DISPLAY"
SCREEN_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_SCREEN"
KEPT_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_KEPT"
HOMES_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_HOMES"
SIZE_SEPARATOR: Final[str] = "x"
ARTIFACTS_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_ARTIFACTS"
REPORT_VARIABLE: Final[str] = "SAMPLETONES_SCREENS_REPORT"
STRICT_HISTORY_VARIABLE: Final[str] = f"{SAMPLETONES_ENV_PREFIX}STRICT_HISTORY"
STRICT_HISTORY: Final[str] = "true"
NO_INPUT_METHOD: Final[str] = "@im=none"
DROPPED_PREFIXES: Final[Tuple[str, ...]] = ("PYTEST_", "WAYLAND_")
UNSAFE_CHARACTERS: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9_.-]+")
DEFAULT_SCREEN_SIZE: Final[ScreenSize] = ScreenSize(width=1600, height=1000)
DEFAULT_DISPLAY_BACKEND: Final[DisplayBackend] = DisplayBackend.XVFB


def display_backend(environment: Mapping[str, str]) -> DisplayBackend:
    """The X server a run draws on: Xvfb unless ``SAMPLETONES_SCREENS_DISPLAY`` names another."""
    return DisplayBackend(environment.get(DISPLAY_BACKEND_VARIABLE, DEFAULT_DISPLAY_BACKEND))


def screen_size(environment: Mapping[str, str]) -> ScreenSize:
    """The pixels a run's screen spans: the default unless ``SAMPLETONES_SCREENS_SCREEN`` reads ``WIDTHxHEIGHT``."""
    stated = environment.get(SCREEN_VARIABLE)
    if stated is None:
        return DEFAULT_SCREEN_SIZE

    width, height = stated.split(SIZE_SEPARATOR)
    return ScreenSize(width=int(width), height=int(height))


def kept_root(environment: Mapping[str, str]) -> Path:
    """The folder a run keeps its reports and failure records under, which ``SAMPLETONES_SCREENS_KEPT`` moves."""
    stated = environment.get(KEPT_VARIABLE)
    return Path(stated) if stated is not None else KEPT_DIRECTORY


def homes_root(environment: Mapping[str, str]) -> Path:
    """The folder the workers make their homes folders in: the system's temporary folder, which
    ``SAMPLETONES_SCREENS_HOMES`` moves.
    """
    stated = environment.get(HOMES_VARIABLE)
    return Path(stated) if stated is not None else Path(tempfile.gettempdir())


@dataclass(frozen=True)
class ScenarioFolders:
    """Where one scenario's run keeps its files: the home its application lives in, and what the run keeps.

    The home is scratch, built afresh from the scenario's world in the worker's homes folder, whose path
    holds no hidden folder, so the application's browsers reach it from any checkout. What the run keeps lies under
    the run's artifacts in the checkout: the reports, a screenshot of a failure, and a copy of the home a
    failed scenario left, with a note where that copy lost files.

    Attributes:
        root: The scenario's folder under the run's artifacts, kept after the run for a reader.
        home: The home directory the application reads and writes as the user's own.
        reports: The file the child process writes its pytest reports to.
    """

    root: Path
    home: Path
    reports: Path

    @classmethod
    def of(
        cls,
        nodeid: str,
        homes: Path,
        kept: Path,
    ) -> ScenarioFolders:
        """The folders of the scenario ``nodeid`` names, under a name a file system accepts.

        Args:
            nodeid: The scenario's pytest node id.
            homes: The folder holding the homes of this worker's scenarios.
            kept: The folder the run keeps every scenario's reports and failure records under.
        """
        name = UNSAFE_CHARACTERS.sub("_", nodeid)
        root = kept / name
        return cls(
            root=root,
            home=homes / name / HOME_FOLDER,
            reports=root / REPORTS_FILE,
        )

    def prepare(self) -> None:
        """Clears what an earlier run of the scenario left, and lays out an empty home and the artifacts folder."""
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.home, ignore_errors=True)
        self.root.mkdir(parents=True)
        self.home.mkdir(parents=True)

    def finish(self, *, failed: bool) -> None:
        """Lets the scratch home go, keeping a copy among the artifacts where the scenario failed.

        A scenario can leave a folder of its home locked, so every folder opens again first. The copy
        keeps what it can read, a note beside the artifacts says what it lost, and the home goes
        however the copy ended.
        """
        reopen_folders(self.home.parent)
        try:
            if failed:
                self._keep_the_home()
        finally:
            let_go(self.home.parent)

    def _keep_the_home(self) -> None:
        try:
            shutil.copytree(self.home, self.root / HOME_FOLDER, symlinks=True)
        except OSError as error:
            (self.root / HOME_COPY_NOTE).write_text(
                f"The copy of the scenario's home is incomplete:\n{error}\n",
                encoding="utf-8",
            )


def child_environment(
    base: Mapping[str, str],
    folders: ScenarioFolders,
    *,
    display: str,
) -> Dict[str, str]:
    """The environment a scenario's process starts under: ``base``, pointed at the scenario's own world.

    The home and every XDG directory lie inside the scenario's home, so settings, session state and
    the documents folder start empty and stay apart from the user's, and from the homes beside it.
    The process makes its temporary files where the machine keeps them, as it does on a user's
    machine, which keeps the socket paths it opens there short. The display is the worker's own
    server, the session bus address leads nowhere, and the input method is off, so everything a
    scenario does stays on its own display and in its own home.
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
