from typing import Final, Iterator

from Xlib import X
from Xlib.display import Display
from Xlib.protocol.event import ClientMessage
from Xlib.xobject.drawable import Window

PROCESS_PROPERTY: Final[str] = "_NET_WM_PID"
PROTOCOLS_PROPERTY: Final[str] = "WM_PROTOCOLS"
DELETE_PROTOCOL: Final[str] = "WM_DELETE_WINDOW"
CLIENT_MESSAGE_FORMAT: Final[int] = 32
UNUSED_FIELD: Final[int] = 0


class MissingWindowError(AssertionError):
    """Raised when no window on the display belongs to the process a scenario drives."""


class WindowManager:
    """What a window manager does to the application's window on a scenario's display.

    The scenario's X server runs no window manager, so the request a manager sends when a user
    presses the close button of a title bar is sent from here, to the window carrying the
    application's process id.
    """

    def __init__(
        self,
        display_name: str,
        process_id: int,
    ) -> None:
        self._display = Display(display_name)
        self._process_id = process_id

    def request_close(self) -> None:
        """Asks the application's window to close, as the close button of its title bar does.

        Raises:
            MissingWindowError: If no window on the display carries the application's process id.
        """
        window = self._own_window()
        message = ClientMessage(
            window=window,
            client_type=self._display.intern_atom(PROTOCOLS_PROPERTY),
            data=(
                CLIENT_MESSAGE_FORMAT,
                [self._display.intern_atom(DELETE_PROTOCOL), X.CurrentTime, UNUSED_FIELD, UNUSED_FIELD, UNUSED_FIELD],
            ),
        )
        window.send_event(message, event_mask=X.NoEventMask)
        self._display.sync()

    def close(self) -> None:
        """Closes the connection to the display."""
        self._display.close()

    def _own_window(self) -> Window:
        process_property = self._display.intern_atom(PROCESS_PROPERTY)
        for window in _windows_under(self._display.screen().root):
            owner = window.get_full_property(process_property, X.AnyPropertyType)
            if owner is not None and list(owner.value) == [self._process_id]:
                return window

        raise MissingWindowError(f"No window on the display carries the process id {self._process_id}")


def _windows_under(window: Window) -> Iterator[Window]:
    for child in window.query_tree().children:
        yield child
        yield from _windows_under(child)
