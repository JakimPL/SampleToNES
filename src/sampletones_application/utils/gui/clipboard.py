import threading
from typing import Protocol, cast

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.dpg import dpg_configure_item


class TextClipboard(Protocol):
    """The clipboard the desktop shares between applications, as text going out and coming back."""

    def read(self) -> str: ...

    def write(self, text: str) -> None: ...


class SystemTextClipboard:
    """The desktop's clipboard, reached through the one DearPyGui holds for the viewport."""

    def read(self) -> str:
        return cast(str, dpg.get_clipboard_text())

    def write(self, text: str) -> None:
        dpg.set_clipboard_text(text)


def copy_to_clipboard(
    text: str,
    label: str,
    button_tag: str,
    *,
    copied_label: str,
) -> None:
    SystemTextClipboard().write(text)

    dpg_configure_item(button_tag, label=copied_label)

    def restore_label() -> None:
        dpg_configure_item(button_tag, label=label)

    timer = threading.Timer(1.0, restore_label)
    timer.start()
