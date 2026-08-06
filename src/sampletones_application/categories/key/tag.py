from __future__ import annotations

from typing import Dict, Final

from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.tags.compose import compose_tag

_PANEL_SHORT_NAMES: Final[Dict[Panel, str]] = {Panel.CONFIG: "config"}


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

        instance: TagName = super().__new__(cls, compose_tag(*parts))
        instance.page = page
        instance.panel = panel
        instance.widget = widget
        instance.element = element
        return instance
