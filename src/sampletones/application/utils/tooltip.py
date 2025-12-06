import dearpygui.dearpygui as dpg

from ..elements.fonts.font import Font
from ..elements.fonts.registry import FontRegistry


def show_tooltip(parent: str, message: str) -> None:
    with dpg.tooltip(parent, hide_on_activity=True):
        tooltip_text = dpg.add_text(message)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)
