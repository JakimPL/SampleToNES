import time
from typing import Optional

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

    def read_text(self, seconds: float) -> Optional[str]:
        """The clipboard's text, or ``None`` where the read went unanswered.

        An owner staying silent past ``seconds`` and a display refusing the connection both leave
        the clipboard's text unknown, which reads as no answer and is logged. A clipboard holding
        nothing answers with an empty text.
        """
        deadline = time.monotonic() + seconds
        try:
            with XcbConnection(self._library, self._display) as connection:
                return SelectionTransfer(connection, deadline=deadline).text()
        except (ConnectionError, TimeoutError) as error:
            logger.warning(f"The clipboard answered nothing: {error}")
            return None
