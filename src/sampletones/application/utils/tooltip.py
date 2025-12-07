import dearpygui.dearpygui as dpg

from sampletones.typehints import Sender

from ..elements.fonts.font import Font
from ..elements.fonts.registry import FontRegistry


def show_tooltip(parent: str, message: str) -> Sender:
    with dpg.tooltip(parent, hide_on_activity=True):
        tooltip_text = dpg.add_text(message)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)

    return tooltip_text
