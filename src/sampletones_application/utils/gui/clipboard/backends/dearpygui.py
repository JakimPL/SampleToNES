from typing import cast

import dearpygui.dearpygui as dpg

from sampletones_shared.types.callback import StringCallback


class DearPyGuiTextClipboard:
    """The desktop's clipboard, reached through the one DearPyGui holds for the viewport.

    The platform's clipboard hands its text over within the call, so a read answers at once.
    """

    def read(self, on_text: StringCallback) -> None:
        on_text(cast(str, dpg.get_clipboard_text()))

    def write(self, text: str) -> None:
        dpg.set_clipboard_text(text)
