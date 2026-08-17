import sys
from importlib.resources import files
from pathlib import Path
from typing import Final, Optional

_BUNDLE_ROOT: Final[Optional[str]] = getattr(sys, "_MEIPASS", None)

CONFIG_DIRECTORY: Final[Path] = (
    Path(_BUNDLE_ROOT) / "config" if _BUNDLE_ROOT is not None else Path(str(files("sampletones_config")))
)

ASSETS_DIRECTORY: Final[str] = "assets"

ICON_DIRECTORY: Final[str] = "icons"
ICON_WIN_FILENAME: Final[str] = "sampletones.ico"
ICON_UNIX_FILENAME: Final[str] = "sampletones.png"

FONT_DIRECTORY: Final[str] = "fonts"
FONT_SANS_REGULAR: Final[str] = "SourceSans3-Regular.ttf"
FONT_SANS_BOLD: Final[str] = "SourceSans3-Bold.ttf"
FONT_SANS_ITALIC: Final[str] = "SourceSans3-Italic.ttf"
FONT_MONO_REGULAR: Final[str] = "RobotoMono-Regular.ttf"
FONT_MONO_BOLD: Final[str] = "RobotoMono-Bold.ttf"
FONT_ICON: Final[str] = "DejaVuSans.ttf"
