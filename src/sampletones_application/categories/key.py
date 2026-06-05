from __future__ import annotations

from typing import Final, NamedTuple

from sampletones_application.categories.abstract import AbstractElement
from sampletones_application.categories.hierarchy import Page, Panel, TextType, Widget

_KEY_SEPARATOR: Final[str] = "."
_PANEL_SHORT_NAMES: Final[dict[Panel, str]] = {Panel.CONFIG_PANEL: "config"}


class TextKey(NamedTuple):
    page: Page
    panel: Panel
    text_type: TextType
    element: AbstractElement

    def compose(self) -> str:
        return _KEY_SEPARATOR.join(str(part) for part in self)  # pylint: disable=not-an-iterable

    def __str__(self) -> str:
        return self.compose()


class TagName(str):
    """Structured tag identifier that inherits from str for seamless
    DearPyGUI integration.

    String value format: page[.panel].widget[.element]
    """

    page: Page
    panel: Panel
    widget: Widget
    element: str

    def __new__(
        cls,
        page: Page,
        panel: Panel,
        widget: Widget,
        element: str,
    ) -> TagName:
        panel_str = _PANEL_SHORT_NAMES.get(panel, str(panel))
        parts = [str(page)]
        if panel != Panel.IMPLICIT:
            parts.append(panel_str)

        parts.append(str(widget))
        if element and element != panel_str:
            parts.append(element)

        instance: TagName = super().__new__(cls, _KEY_SEPARATOR.join(parts))
        instance.page = page
        instance.panel = panel
        instance.widget = widget
        instance.element = element
        return instance
