from enum import Enum

from sampletones_shared.paths.resources import (
    FONT_ICON,
    FONT_MONO_BOLD,
    FONT_MONO_REGULAR,
    FONT_SANS_BOLD,
    FONT_SANS_ITALIC,
    FONT_SANS_REGULAR,
    ICON_UNIX_FILENAME,
    ICON_WIN_FILENAME,
)


class IconResource(Enum):
    UNIX = ICON_UNIX_FILENAME
    WIN = ICON_WIN_FILENAME


class FontResource(Enum):
    REGULAR = FONT_SANS_REGULAR
    BOLD = FONT_SANS_BOLD
    ITALIC = FONT_SANS_ITALIC
    MONO = FONT_MONO_REGULAR
    MONO_BOLD = FONT_MONO_BOLD
    ICON = FONT_ICON
