import threading

import dearpygui.dearpygui as dpg

from ..constants import LBL_COPIED_TOOLTIP
from .dpg import dpg_configure_item, dpg_get_item_label


def copy_to_clipboard(text: str, button_tag: str) -> None:
    dpg.set_clipboard_text(text)

    original_label = dpg_get_item_label(button_tag)
    dpg_configure_item(button_tag, label=LBL_COPIED_TOOLTIP)

    def restore_label():
        dpg_configure_item(button_tag, label=original_label)

    timer = threading.Timer(1.0, restore_label)
    timer.start()
