from typing import Final, List, Optional, Protocol, Tuple

from sampletones_application.utils.gui.clipboard.backends.x11.connection import (
    PropertyNotify,
    PropertyValue,
    SelectionEvent,
    SelectionNotify,
)

CLIPBOARD: Final[str] = "CLIPBOARD"
INCREMENTAL: Final[str] = "INCR"
LANDING_PROPERTY: Final[str] = "SAMPLETONES_CLIPBOARD"
NO_WINDOW: Final[int] = 0
NO_PROPERTY: Final[int] = 0
TEXT_TARGETS: Final[Tuple[Tuple[str, str], ...]] = (
    ("UTF8_STRING", "utf-8"),
    ("STRING", "latin-1"),
)
UNREADABLE_BYTES: Final[str] = "replace"


class SelectionConnection(Protocol):
    """The calls a selection transfer makes on its connection to the X server."""

    def atom(self, name: str) -> int: ...

    def selection_owner(self, selection: int) -> int: ...

    def create_requestor(self) -> int: ...

    def convert_selection(
        self,
        *,
        requestor: int,
        selection: int,
        target: int,
        landing: int,
    ) -> None: ...

    def take_property(self, window: int, atom: int) -> PropertyValue: ...

    def next_event(self, deadline: float) -> Optional[SelectionEvent]: ...


class SelectionTransfer:
    """One conversation with the application holding the clipboard, carrying its text across.

    The conversation is the one the ICCCM lays out: the requestor asks the owner to convert the
    clipboard to a text type, the owner writes the text to a property of the requestor's window
    and says so, and a long text comes in pieces, each written once the requestor has taken the
    one before. UTF-8 is asked for first and Latin-1 after it, the order GLFW asks in.

    The whole conversation runs until ``deadline``, read against ``time.monotonic``, and an owner
    still silent then ends it with a :class:`TimeoutError`.
    """

    def __init__(self, connection: SelectionConnection, *, deadline: float) -> None:
        self._connection = connection
        self._deadline = deadline

    def text(self) -> str:
        """The clipboard's text, an empty one where it holds nothing a reader can take.

        Raises:
            TimeoutError: If the application holding the clipboard answers nothing in time.
        """
        clipboard = self._connection.atom(CLIPBOARD)
        if self._connection.selection_owner(clipboard) == NO_WINDOW:
            return ""

        return self._first_text(clipboard)

    def _first_text(self, clipboard: int) -> str:
        """The clipboard's text in the first type the owner writes it as, or an empty text."""
        requestor = self._connection.create_requestor()
        landing = self._connection.atom(LANDING_PROPERTY)
        for target, encoding in TEXT_TARGETS:
            data = self._convert(clipboard, self._connection.atom(target), requestor, landing)
            if data is not None:
                return data.decode(encoding, errors=UNREADABLE_BYTES)

        return ""

    def _convert(
        self,
        clipboard: int,
        target: int,
        requestor: int,
        landing: int,
    ) -> Optional[bytes]:
        """The clipboard's bytes as ``target``, or ``None`` once the owner declines that type."""
        self._connection.convert_selection(
            requestor=requestor,
            selection=clipboard,
            target=target,
            landing=landing,
        )
        if self._await_notify(requestor) == NO_PROPERTY:
            return None

        value = self._connection.take_property(requestor, landing)
        if value.value_type != self._connection.atom(INCREMENTAL):
            return value.data

        return self._receive_pieces(requestor, landing)

    def _await_notify(self, requestor: int) -> int:
        """The property the owner names in its answer, the changes announced ahead of it passed over."""
        while True:
            match self._next_event():
                case SelectionNotify(requestor=answered, landing=landing) if answered == requestor:
                    return landing

    def _receive_pieces(self, requestor: int, landing: int) -> bytes:
        """Takes each piece as the owner writes it, until the empty piece that closes the text."""
        pieces: List[bytes] = []
        while True:
            match self._next_event():
                case PropertyNotify(window=window, atom=atom, new_value=True) if (window, atom) == (requestor, landing):
                    piece = self._connection.take_property(requestor, landing).data
                    if not piece:
                        return b"".join(pieces)

                    pieces.append(piece)

    def _next_event(self) -> SelectionEvent:
        """The next event the owner's side of the conversation brings.

        Raises:
            TimeoutError: If the deadline passes before the next event.
        """
        event = self._connection.next_event(self._deadline)
        if event is None:
            raise TimeoutError("The application holding the clipboard answered nothing in time")

        return event
