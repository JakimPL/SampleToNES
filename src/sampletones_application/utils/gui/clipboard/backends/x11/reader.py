import time

from sampletones_application.utils.gui.clipboard.backends.x11.connection import XcbConnection
from sampletones_application.utils.gui.clipboard.backends.x11.library import XcbLibrary
from sampletones_application.utils.gui.clipboard.backends.x11.transfer import SelectionTransfer
from sampletones_shared.logger import logger


class XcbSelectionReader:
    """Reads the clipboard's text over a connection of its own to ``display``, one per read.

    A fresh connection leaves nothing behind from a read before it, so an answer arriving after
    its deadline lands on a connection already closed.
    """

    def __init__(self, library: XcbLibrary, display: str) -> None:
        self._library = library
        self._display = display

    def read_text(self, seconds: float) -> str:
        """The clipboard's text, or an empty text once ``seconds`` pass before the owner hands it over.

        A display that refuses the connection reads as an empty clipboard too, and is logged.
        """
        deadline = time.monotonic() + seconds
        try:
            with XcbConnection(self._library, self._display) as connection:
                return SelectionTransfer(connection, deadline=deadline).text()
        except ConnectionError as error:
            logger.warning(f"The clipboard was read as empty: {error}")
            return ""
