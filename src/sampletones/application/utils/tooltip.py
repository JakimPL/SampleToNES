import dearpygui.dearpygui as dpg

from sampletones.typehints import Sender

from ..constants.general import TAG_STATUS_BAR
from ..elements.fonts.font import Font
from ..elements.fonts.registry import FontRegistry


def show_tooltip(parent: str, message: str) -> Sender:
    with dpg.tooltip(parent, hide_on_activity=True):
        tooltip_text: Sender = dpg.add_text(message)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)

    return tooltip_text


def show_status(message: str) -> None:
    dpg.set_value(TAG_STATUS_BAR, message)
