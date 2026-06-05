from pathlib import Path
from typing import Final

from sampletones_core.paths import (
    APPLICATION_CONFIG_PATH,
    CONFIG_PATH,
    LIBRARY_DIRECTORY,
    OUTPUT_DIRECTORY,
    PROJECTS_DIRECTORY,
    USER_PATH_CONFIG,
)

APPLICATION_STATE_PATH: Final[Path] = USER_PATH_CONFIG / "sampletones_state.yaml"

__all__ = [
    "APPLICATION_CONFIG_PATH",
    "APPLICATION_STATE_PATH",
    "CONFIG_PATH",
    "LIBRARY_DIRECTORY",
    "OUTPUT_DIRECTORY",
    "PROJECTS_DIRECTORY",
    "CONFIG_DIRECTORY",
    "LAYOUT_DIRECTORY",
    "BEHAVIOR_DIRECTORY",
    "LANG_DIRECTORY",
    "LANG_EN",
]

PROJECT_ROOT: Final[Path] = Path(__file__).parents[2]
CONFIG_DIRECTORY: Final[Path] = PROJECT_ROOT / "config"
LAYOUT_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "layout"
BEHAVIOR_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "behavior"
LANG_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "lang"
LANG_EN: Final[Path] = LANG_DIRECTORY / "en.yaml"
