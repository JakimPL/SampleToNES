from functools import partial
from typing import Final

from sampletones_application.utils.callbacks.delay import call_after
from sampletones_application.utils.gui.clipboard.selection import select_text_clipboard
from sampletones_application.utils.gui.dpg import dpg_configure_item

COPIED_LABEL_SECONDS: Final[float] = 1.0


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
    select_text_clipboard().write(text)

    dpg_configure_item(button_tag, label=copied_label)
    call_after(COPIED_LABEL_SECONDS, partial(dpg_configure_item, button_tag, label=label))
