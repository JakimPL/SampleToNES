import threading

import dearpygui.dearpygui as dpg

from ..constants import LBL_COPIED_TOOLTIP
from .dpg import dpg_configure_item


def copy_to_clipboard(text: str, label: str, button_tag: str) -> None:
    dpg.set_clipboard_text(text)

    dpg_configure_item(button_tag, label=LBL_COPIED_TOOLTIP)

    def restore_label():
        dpg_configure_item(button_tag, label=label)

    timer = threading.Timer(1.0, restore_label)
    timer.start()
