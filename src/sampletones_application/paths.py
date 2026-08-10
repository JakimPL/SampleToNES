from pathlib import Path
from typing import Final

from sampletones_core.paths import USER_PATH_CONFIG
from sampletones_shared.paths import CONFIG_DIRECTORY

APPLICATION_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "application"
BEHAVIOR_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "behavior"
KEYBINDINGS_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "keybindings"
LAYOUT_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "layout"
PALETTES_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "palettes"
LANG_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "lang"
THEME_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "theme"

LANG_EN: Final[Path] = LANG_DIRECTORY / "en.yaml"
DEPLOYMENT_CONFIG_PATH: Final[Path] = APPLICATION_DIRECTORY / "deployment.yaml"
APPLICATION_STATE_PATH: Final[Path] = USER_PATH_CONFIG / "state.yaml"
