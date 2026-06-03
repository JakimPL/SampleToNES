from pathlib import Path
from typing import Final

from sampletones_core.constants.paths import (
    APPLICATION_CONFIG_PATH,
    CONFIG_PATH,
    LIBRARY_DIRECTORY,
    OUTPUT_DIRECTORY,
)

__all__ = [
    "APPLICATION_CONFIG_PATH",
    "CONFIG_PATH",
    "LIBRARY_DIRECTORY",
    "OUTPUT_DIRECTORY",
    "CONFIG_DIR",
    "LAYOUT_DIR",
    "BEHAVIOR_DIR",
    "LANG_DIR",
    "LANG_EN",
]

# Project-level config directory (SampleToNES/config/), three levels above this file
CONFIG_DIR: Final[Path] = Path(__file__).parents[2] / "config"
LAYOUT_DIR: Final[Path] = CONFIG_DIR / "layout"
BEHAVIOR_DIR: Final[Path] = CONFIG_DIR / "behavior"
LANG_DIR: Final[Path] = CONFIG_DIR / "lang"
LANG_EN: Final[Path] = LANG_DIR / "en.yaml"
