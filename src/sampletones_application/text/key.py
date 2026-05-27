from typing import Final, NamedTuple

from sampletones_application.text.abstract import AbstractElement
from sampletones_application.text.hierarchy import Page, Panel, TextType

_KEY_SEPARATOR: Final[str] = "."


class TextKey(NamedTuple):
    page: Page
    panel: Panel
    text_type: TextType
    element: AbstractElement

    def compose(self) -> str:
        return _KEY_SEPARATOR.join(str(part) for part in self)  # pylint: disable=not-an-iterable
