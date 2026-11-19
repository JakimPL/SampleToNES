from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.resources import FONTS_PACKAGE, ICON_VECTOR_FILENAME, ICONS_PACKAGE

STATIC_PACKAGE: Final[str] = "sampletones_tools.web.static"

STATIC_DIRECTORY: Final[Path] = package_directory(STATIC_PACKAGE)
FONTS_DIRECTORY: Final[Path] = package_directory(FONTS_PACKAGE)
MARK_SOURCE: Final[Path] = package_directory(ICONS_PACKAGE) / ICON_VECTOR_FILENAME
