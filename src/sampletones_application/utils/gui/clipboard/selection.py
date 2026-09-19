import os
from typing import Final, Optional

from sampletones_application.utils.gui.clipboard.backends.dearpygui import DearPyGuiTextClipboard
from sampletones_application.utils.gui.clipboard.backends.x11.clipboard import X11TextClipboard
from sampletones_application.utils.gui.clipboard.backends.x11.library import load_xcb
from sampletones_application.utils.gui.clipboard.backends.x11.reader import XcbSelectionReader
from sampletones_application.utils.gui.clipboard.protocol import TextClipboard
from sampletones_shared.utils.system.system import System

DISPLAY_VARIABLE: Final[str] = "DISPLAY"


def select_text_clipboard() -> TextClipboard:
    """Returns the clipboard implementation that fits the running environment.

    On Linux, DearPyGui draws on an X display, and the X11 clipboard reads over a connection of its
    own to that same display while libxcb, which the X client library itself stands on, loads. On
    other platforms DearPyGui's own clipboard serves reads and writes alike.
    """
    match System.current():
        case System.LINUX:
            return _x11_clipboard() or DearPyGuiTextClipboard()
        case _:
            return DearPyGuiTextClipboard()


def _x11_clipboard() -> Optional[TextClipboard]:
    display = os.environ.get(DISPLAY_VARIABLE)
    library = load_xcb()
    if not display or library is None:
        return None

    return X11TextClipboard(XcbSelectionReader(library, display))
