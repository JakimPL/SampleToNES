from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS

CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_tools.tracker_playback.config")
CORPUS_PATH: Final[Path] = CONFIG_DIRECTORY / "corpus.yaml"
SETTINGS_PATH: Final[Path] = CONFIG_DIRECTORY / "settings.yaml"
BITPHASE_SCRIPT_DIRECTORY: Final[Path] = package_directory(
    "sampletones_tools.tracker_playback.targets.bitphase.script",
)
BITPHASE_TRACE_SCRIPT_PATH: Final[Path] = BITPHASE_SCRIPT_DIRECTORY / "trace.mts"
OUTPUT_ROOT: Final[Path] = USER_PATH_DOCUMENTS / "tracker-playback"
DOCUMENTS_DIRECTORY_NAME: Final[str] = "documents"
REPORT_FILENAME: Final[str] = "report.md"
