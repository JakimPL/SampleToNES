from pathlib import Path
from typing import Final

from sampletones_shared.paths.source import REPOSITORY_ROOT

SCREENS_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "tests" / "screens"
SCREEN_DRIVER_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "tests" / "suite" / "screens"
DEARPYGUI_LAYER_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "tests" / "suite" / "screens" / "dearpygui"
ARTIFACTS_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "build" / "screens"
HOME_FOLDER: Final[str] = "home"
HOMES_PREFIX: Final[str] = "sampletones-screens-"
HOME_COPY_NOTE: Final[str] = "home-copy-incomplete.txt"
PROCESSES_DIRECTORY: Final[Path] = Path("/proc")
REPORTS_FILE: Final[str] = "reports.jsonl"
NO_BUS_FILE: Final[str] = "no-bus"
FAILURE_SCREENSHOT: Final[str] = "failure.png"
