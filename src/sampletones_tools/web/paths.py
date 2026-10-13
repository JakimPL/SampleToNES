from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.resources import ICON_VECTOR_FILENAME

STATIC_PACKAGE: Final[str] = "sampletones_tools.web.static"
FONTS_PACKAGE: Final[str] = "sampletones_assets.fonts"
ICONS_PACKAGE: Final[str] = "sampletones_assets.icons"

STATIC_DIRECTORY: Final[Path] = package_directory(STATIC_PACKAGE)
FONTS_DIRECTORY: Final[Path] = package_directory(FONTS_PACKAGE)
MARK_SOURCE: Final[Path] = package_directory(ICONS_PACKAGE) / ICON_VECTOR_FILENAME
