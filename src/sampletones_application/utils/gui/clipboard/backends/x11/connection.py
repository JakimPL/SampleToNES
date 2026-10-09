from __future__ import annotations

import ctypes
import select
import time
from dataclasses import dataclass
from enum import IntEnum
from types import TracebackType
from typing import Any, Final, Optional, Type, Union

from sampletones_application.utils.gui.clipboard.backends.x11.library import (
    Cookie,
    GenericEvent,
    PropertyNotifyEvent,
    Screen,
    SelectionNotifyEvent,
    XcbLibrary,
)

SENT_EVENT_BIT: Final[int] = 0x80
PROPERTY_NEW_VALUE: Final[int] = 0
COPY_FROM_PARENT: Final[int] = 0
INPUT_ONLY_WINDOW: Final[int] = 2
EVENT_MASK_VALUE: Final[int] = 1 << 11
PROPERTY_CHANGE_EVENTS: Final[int] = 1 << 22
CURRENT_TIME: Final[int] = 0
ANY_PROPERTY_TYPE: Final[int] = 0
DELETE_AFTER_READING: Final[int] = 1
WHOLE_PROPERTY_WORDS: Final[int] = 0x3FFFFFFF


class EventCode(IntEnum):
    PROPERTY_NOTIFY = 28
    SELECTION_NOTIFY = 31


@dataclass(frozen=True)
class SelectionNotify:
    """The owner's answer to a conversion: the property it wrote the text to, or none at all."""

    requestor: int
    landing: int


@dataclass(frozen=True)
class PropertyNotify:
    """A property on a window changed, which is how a text sent in pieces announces each piece."""

    window: int
    atom: int
    new_value: bool


SelectionEvent = Union[SelectionNotify, PropertyNotify]


@dataclass(frozen=True)
class PropertyValue:
    """What a window property held when it was read: its type and its bytes."""

    value_type: int
    data: bytes


class XcbConnection:
    """A connection of our own to the X server, speaking the calls a selection transfer makes.

    A connection carries its own requests and events, so a transfer run on it stays apart from the
    one DearPyGui draws through. Every call that waits on the server asks the X server alone, which
    answers right away; the owner of the clipboard is heard from through events, which
    :meth:`next_event` waits for until a deadline.

    Raises:
        ConnectionError: If the display refuses the connection or the connection breaks.
    """

    def __init__(self, library: XcbLibrary, display: str) -> None:
        self._library = library
        self._handle: int = library.connect(display.encode(), None)
        if library.connection_has_error(self._handle):
            library.disconnect(self._handle)
            raise ConnectionError(f"The X display {display} refused a connection")

    def __enter__(self) -> XcbConnection:
        return self

    def __exit__(
        self,
        _exception_type: Optional[Type[BaseException]],
        _exception: Optional[BaseException],
        _traceback: Optional[TracebackType],
    ) -> None:
        self._library.disconnect(self._handle)

    def atom(self, name: str) -> int:
        encoded = name.encode()
        cookie = self._library.intern_atom(self._handle, 0, len(encoded), encoded)
        reply = self._library.intern_atom_reply(self._handle, cookie, None)
        self._require(reply)
        atom = int(reply.contents.atom)
        self._library.free(reply)
        return atom

    def selection_owner(self, selection: int) -> int:
        cookie = self._library.get_selection_owner(self._handle, selection)
        reply = self._library.get_selection_owner_reply(self._handle, cookie, None)
        self._require(reply)
        owner = int(reply.contents.owner)
        self._library.free(reply)
        return owner

    def create_requestor(self) -> int:
        """Creates the window an owner writes the text to, reporting each change to its properties."""
        roots = self._library.setup_roots_iterator(self._library.get_setup(self._handle))
        screen = ctypes.cast(roots.data, ctypes.POINTER(Screen)).contents
        window = int(self._library.generate_id(self._handle))
        events = ctypes.c_uint32(PROPERTY_CHANGE_EVENTS)
        self._library.create_window(
            self._handle,
            COPY_FROM_PARENT,
            window,
            screen.root,
            0,
            0,
            1,
            1,
            0,
            INPUT_ONLY_WINDOW,
            COPY_FROM_PARENT,
            EVENT_MASK_VALUE,
            ctypes.byref(events),
        )
        return window

    def convert_selection(
        self,
        *,
        requestor: int,
        selection: int,
        target: int,
        landing: int,
    ) -> None:
        """Asks the owner of ``selection`` to write it as ``target`` to ``landing`` on ``requestor``."""
        self._library.convert_selection(self._handle, requestor, selection, target, landing, CURRENT_TIME)
        self._library.flush(self._handle)

    def take_property(self, window: int, atom: int) -> PropertyValue:
        """Reads a property whole and deletes it, which an owner sending in pieces waits for."""
        cookie: Cookie = self._library.get_property(
            self._handle,
            DELETE_AFTER_READING,
            window,
            atom,
            ANY_PROPERTY_TYPE,
            0,
            WHOLE_PROPERTY_WORDS,
        )
        reply = self._library.get_property_reply(self._handle, cookie, None)
        self._require(reply)
        value_type = int(reply.contents.type)
        data = ctypes.string_at(
            self._library.get_property_value(reply),
            self._library.get_property_value_length(reply),
        )
        self._library.free(reply)
        self._library.flush(self._handle)
        return PropertyValue(value_type=value_type, data=data)

    def next_event(self, deadline: float) -> Optional[SelectionEvent]:
        """The next selection or property event, or ``None`` once ``deadline`` passes first.

        ``deadline`` is read against ``time.monotonic``. Events of any other kind are passed over.
        """
        while True:
            raw = self._poll_event()
            if raw is not None:
                event = self._selection_event(raw)
                if event is not None:
                    return event

                continue

            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                return None

            select.select([self._library.get_file_descriptor(self._handle)], [], [], remaining)

    def _poll_event(self) -> Optional[bytes]:
        """The next event libxcb has read, as its raw bytes, while one is waiting."""
        event = self._library.poll_for_event(self._handle)
        if not event:
            if self._library.connection_has_error(self._handle):
                raise ConnectionError("The connection to the X display broke")

            return None

        raw = ctypes.string_at(event, ctypes.sizeof(GenericEvent))
        self._library.free(event)
        return raw

    @staticmethod
    def _selection_event(raw: bytes) -> Optional[SelectionEvent]:
        match raw[0] & ~SENT_EVENT_BIT:
            case EventCode.SELECTION_NOTIFY:
                notify = SelectionNotifyEvent.from_buffer_copy(raw)
                return SelectionNotify(requestor=notify.requestor, landing=notify.property)
            case EventCode.PROPERTY_NOTIFY:
                changed = PropertyNotifyEvent.from_buffer_copy(raw)
                return PropertyNotify(
                    window=changed.window,
                    atom=changed.atom,
                    new_value=changed.state == PROPERTY_NEW_VALUE,
                )

        return None

    @staticmethod
    def _require(reply: Any) -> None:
        """Stops the transfer once the server's reply is missing, which a broken connection leaves."""
        if not reply:
            raise ConnectionError("The X display answered no reply")
