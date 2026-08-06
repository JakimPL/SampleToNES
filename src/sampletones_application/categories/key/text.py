from typing import NamedTuple, Tuple, Union

from sampletones_application.categories.abstract import AbstractElement
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.tags.compose import compose_tag


class TextKey(NamedTuple):
    """The four hierarchy members that name one piece of interface text."""

    page: Page
    panel: Panel
    text_type: TextType
    element: AbstractElement

    def compose(self) -> str:
        return compose_tag(*(str(part) for part in self))  # pylint: disable=not-an-iterable

    def __str__(self) -> str:
        return self.compose()


TextKeyTuple = Tuple[Page, Panel, TextType, AbstractElement]


def compose_text_key(key: Union[str, TextKey, TextKeyTuple]) -> str:
    """Spells any accepted form of a text key as the dotted string the language file is keyed by.

    Args:
        key: A dotted key as `en.yaml` spells it, a `TextKey`, or the four hierarchy members.

    Returns:
        str: The dotted text key.
    """
    match key:
        case str():
            return key
        case TextKey():
            return key.compose()
        case _:
            return TextKey(*key).compose()
