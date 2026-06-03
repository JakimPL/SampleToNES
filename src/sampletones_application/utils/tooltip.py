import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_STATUS_BAR_GLOBAL
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_shared.types.application import Sender


def show_tooltip(parent: str, message: str) -> Sender:
    with dpg.tooltip(parent, hide_on_activity=True):
        tooltip_text: Sender = dpg.add_text(message)
        FontRegistry.bind_to_item(tooltip_text, Font.REGULAR_SMALL)

    return tooltip_text


def show_status(message: str) -> None:
    dpg.set_value(TAG_STATUS_BAR_GLOBAL, message)
