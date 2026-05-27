from enum import Enum

from sampletones_core.constants.paths import ICON_UNIX_FILENAME, ICON_WIN_FILENAME


class IconResource(Enum):
    UNIX = ICON_UNIX_FILENAME
    WIN = ICON_WIN_FILENAME


class FontResource(Enum):
    REGULAR = "RobotoMono-Regular.ttf"
    BOLD = "RobotoMono-Bold.ttf"
    ITALIC = "RobotoMono-Italic.ttf"
    BOLD_ITALIC = "RobotoMono-BoldItalic.ttf"
    ICON = "DejaVuSans.ttf"
