from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Tuple

from tests.screens.prompts.every_door.constants import EXIT
from tests.suite.screens.vocabulary.dialogs import CLOSE


class Door(StrEnum):
    """A gesture that puts the open document away, to replace it or to leave.

    A voice opens from a double-click on its row and from Edit on its row's menu.
    """

    BROWSER = "browser"
    MENU_OPEN = "menu_open"
    CLOSE = "close"
    VOICE = "voice"
    VOICE_MENU = "voice_menu"
    CONVERSION_LOAD = "conversion_load"
    EXIT = "exit"
    WINDOW_CLOSE = "window_close"


ASKING_DOORS: Final[Tuple[Door, ...]] = tuple(Door)


@dataclass(frozen=True)
class Question:
    """A question as the reader meets it, with its title, its words and the answers it offers."""

    title: str
    words: str
    answers: Tuple[str, ...]


@dataclass(frozen=True)
class Standing:
    """What the screen shows of the open document, which a question taken back keeps as it was."""

    title: str
    file_line: str
    volume: str
    windows: Tuple[str, ...]
    dialogs: int
