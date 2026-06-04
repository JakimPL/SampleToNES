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
    """Structured tag identifier that inherits from str for seamless dpg integration."""

    def __new__(
        cls,
        page: Page,
        panel: Panel,
        widget: Widget,
        element: str,
    ) -> TagName:
        parts = [str(widget), str(page)]
        if panel != Panel.IMPLICIT:
            panel_str = _PANEL_SHORT_NAMES.get(panel, str(panel))
            parts.append(panel_str)

        if element and element != str(panel):
            parts.append(str(element))

        tag_str = "_".join(parts)
        instance: TagName = super().__new__(cls, tag_str)
        instance.page = page
        instance.panel = panel
        instance.widget = widget
        instance.element = element
        return instance
