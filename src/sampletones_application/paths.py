from pathlib import Path
from typing import Final

from sampletones_core.paths import USER_PATH_CONFIG

PROJECT_ROOT: Final[Path] = Path(__file__).parents[2]
CONFIG_DIRECTORY: Final[Path] = PROJECT_ROOT / "config"
LAYOUT_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "layout"
BEHAVIOR_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "behavior"
LANG_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "lang"
LANG_EN: Final[Path] = LANG_DIRECTORY / "en.yaml"

APPLICATION_STATE_PATH: Final[Path] = USER_PATH_CONFIG / "state.yaml"
