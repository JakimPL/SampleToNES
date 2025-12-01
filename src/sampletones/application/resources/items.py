from enum import Enum

from sampletones.constants.paths import ICON_UNIX_FILENAME, ICON_WIN_FILENAME


class IconResource(Enum):
    UNIX = ICON_UNIX_FILENAME
    WIN = ICON_WIN_FILENAME


class FontResource(Enum):
    MAIN = "RobotoMono-Regular.ttf"
    BOLD = "RobotoMono-Bold.ttf"
    ITALIC = "RobotoMono-Italic.ttf"
    BOLD_ITALIC = "RobotoMono-BoldItalic.ttf"
