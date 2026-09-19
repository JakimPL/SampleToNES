from functools import partial
from typing import Final, Protocol, cast

import dearpygui.dearpygui as dpg

from sampletones_application.utils.callbacks.delay import call_after
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_shared.types.callback import StringCallback

COPIED_LABEL_SECONDS: Final[float] = 1.0


class TextClipboard(Protocol):
    """The clipboard the desktop shares between applications, as text going out and coming back.

    The application holding the clipboard hands its text over in its own time, so a read names what
    receives the text once it has arrived.
    """

    def read(self, on_text: StringCallback) -> None:
        """Hands the text standing on the clipboard to ``on_text``, on the render thread."""

    def write(self, text: str) -> None: ...


class SystemTextClipboard:
    """The desktop's clipboard, reached through the one DearPyGui holds for the viewport."""

    def read(self, on_text: StringCallback) -> None:
        on_text(cast(str, dpg.get_clipboard_text()))

    def write(self, text: str) -> None:
        dpg.set_clipboard_text(text)


def copy_to_clipboard(
    text: str,
    label: str,
    button_tag: str,
    *,
    copied_label: str,
) -> None:
    """Puts ``text`` on the clipboard, with the button reading ``copied_label`` for a moment.

    The button's own label comes back on the render thread once the moment has passed, the thread
    the button lives on.
    """
    SystemTextClipboard().write(text)

    dpg_configure_item(button_tag, label=copied_label)
    call_after(COPIED_LABEL_SECONDS, partial(dpg_configure_item, button_tag, label=label))
