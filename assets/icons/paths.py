from pathlib import Path
from typing import Final

from sampletones_shared.paths.resources import ASSETS_PACKAGE, ICON_DIRECTORY
from sampletones_shared.paths.source import SOURCE_ROOT

ICONS_DIRECTORY: Final[Path] = SOURCE_ROOT / ASSETS_PACKAGE / ICON_DIRECTORY
