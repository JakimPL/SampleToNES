import sys
from pathlib import Path
from typing import Final

import sampletones_config as _config_pkg
from sampletones_core.paths import USER_PATH_CONFIG

_MEIPASS = getattr(sys, "_MEIPASS", None)
CONFIG_DIRECTORY: Final[Path] = Path(_MEIPASS) / "config" if _MEIPASS is not None else Path(_config_pkg.__file__).parent
BEHAVIOR_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "behavior"
LAYOUT_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "layout"
LANG_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "lang"
THEME_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "theme"
LANG_EN: Final[Path] = LANG_DIRECTORY / "en.yaml"


APPLICATION_STATE_PATH: Final[Path] = USER_PATH_CONFIG / "state.yaml"
