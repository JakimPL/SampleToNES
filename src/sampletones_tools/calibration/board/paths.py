from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory

STATIC_PACKAGE: Final[str] = "sampletones_tools.calibration.board.static"
FONTS_PACKAGE: Final[str] = "sampletones_assets.fonts"

STATIC_DIRECTORY: Final[Path] = package_directory(STATIC_PACKAGE)
FONTS_DIRECTORY: Final[Path] = package_directory(FONTS_PACKAGE)
