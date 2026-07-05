from enum import Enum

from sampletones_core.paths import (
    FONT_BOLD,
    FONT_BOLD_ITALIC,
    FONT_ICON,
    FONT_ITALIC,
    FONT_MAIN,
    ICON_UNIX_FILENAME,
    ICON_WIN_FILENAME,
)


class IconResource(Enum):
    UNIX = ICON_UNIX_FILENAME
    WIN = ICON_WIN_FILENAME


class FontResource(Enum):
    REGULAR = FONT_MAIN
    BOLD = FONT_BOLD
    ITALIC = FONT_ITALIC
    BOLD_ITALIC = FONT_BOLD_ITALIC
    ICON = FONT_ICON
