from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory

CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_config")

ICON_DIRECTORY: Final[str] = "icons"
ICON_WIN_FILENAME: Final[str] = "sampletones.ico"
ICON_UNIX_FILENAME: Final[str] = "sampletones.png"
ICON_VECTOR_FILENAME: Final[str] = "sampletones.svg"

FONT_DIRECTORY: Final[str] = "fonts"
FONT_SANS_REGULAR: Final[str] = "SourceSans3-Regular.ttf"
FONT_SANS_BOLD: Final[str] = "SourceSans3-Bold.ttf"
FONT_SANS_ITALIC: Final[str] = "SourceSans3-Italic.ttf"
FONT_MONO_REGULAR: Final[str] = "RobotoMono-Regular.ttf"
FONT_MONO_BOLD: Final[str] = "RobotoMono-Bold.ttf"
FONT_ICON: Final[str] = "DejaVuSans.ttf"
