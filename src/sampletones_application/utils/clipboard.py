import threading

import dearpygui.dearpygui as dpg

from sampletones_application.utils.dpg import dpg_configure_item


def copy_to_clipboard(text: str, label: str, button_tag: str, *, copied_label: str) -> None:
    dpg.set_clipboard_text(text)

    dpg_configure_item(button_tag, label=copied_label)

    def restore_label() -> None:
        dpg_configure_item(button_tag, label=label)

    timer = threading.Timer(1.0, restore_label)
    timer.start()
