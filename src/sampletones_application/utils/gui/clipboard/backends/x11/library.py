import ctypes
from functools import cache
from typing import Any, Final, Optional

XCB_LIBRARY: Final[str] = "libxcb.so.1"


class Cookie(ctypes.Structure):
    _fields_ = [("sequence", ctypes.c_uint)]


class ScreenIterator(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_void_p),
        ("rem", ctypes.c_int),
        ("index", ctypes.c_int),
    ]


class Screen(ctypes.Structure):
    """A screen as libxcb lays it out, read as far as the root window it opens with."""

    _fields_ = [("root", ctypes.c_uint32)]


class InternAtomReply(ctypes.Structure):
    _fields_ = [
        ("response_type", ctypes.c_uint8),
        ("pad0", ctypes.c_uint8),
        ("sequence", ctypes.c_uint16),
        ("length", ctypes.c_uint32),
        ("atom", ctypes.c_uint32),
    ]


class SelectionOwnerReply(ctypes.Structure):
    _fields_ = [
        ("response_type", ctypes.c_uint8),
        ("pad0", ctypes.c_uint8),
        ("sequence", ctypes.c_uint16),
        ("length", ctypes.c_uint32),
        ("owner", ctypes.c_uint32),
    ]


class PropertyReply(ctypes.Structure):
    _fields_ = [
        ("response_type", ctypes.c_uint8),
        ("format", ctypes.c_uint8),
        ("sequence", ctypes.c_uint16),
        ("length", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("bytes_after", ctypes.c_uint32),
        ("value_len", ctypes.c_uint32),
        ("pad0", ctypes.c_uint8 * 12),
    ]


class GenericEvent(ctypes.Structure):
    _fields_ = [
        ("response_type", ctypes.c_uint8),
        ("body", ctypes.c_uint8 * 31),
    ]


class SelectionNotifyEvent(ctypes.Structure):
    _fields_ = [
        ("response_type", ctypes.c_uint8),
        ("pad0", ctypes.c_uint8),
        ("sequence", ctypes.c_uint16),
        ("time", ctypes.c_uint32),
        ("requestor", ctypes.c_uint32),
        ("selection", ctypes.c_uint32),
        ("target", ctypes.c_uint32),
        ("property", ctypes.c_uint32),
    ]


class PropertyNotifyEvent(ctypes.Structure):
    _fields_ = [
        ("response_type", ctypes.c_uint8),
        ("pad0", ctypes.c_uint8),
        ("sequence", ctypes.c_uint16),
        ("window", ctypes.c_uint32),
        ("atom", ctypes.c_uint32),
        ("time", ctypes.c_uint32),
        ("state", ctypes.c_uint8),
    ]


class XcbLibrary:
    """libxcb as ctypes reaches it, each call declared with the C types it takes and returns.

    Replies and events arrive in memory libxcb allocated, and the C library's ``free`` releases
    them, so it is declared here beside the calls that hand them out.
    """

    def __init__(self, library: ctypes.CDLL) -> None:
        connection = ctypes.c_void_p
        window = ctypes.c_uint32
        atom = ctypes.c_uint32
        self.free = self._declare(ctypes.CDLL(None).free, None, ctypes.c_void_p)
        self.connect = self._declare(library.xcb_connect, connection, ctypes.c_char_p, ctypes.c_void_p)
        self.connection_has_error = self._declare(library.xcb_connection_has_error, ctypes.c_int, connection)
        self.disconnect = self._declare(library.xcb_disconnect, None, connection)
        self.flush = self._declare(library.xcb_flush, ctypes.c_int, connection)
        self.get_file_descriptor = self._declare(library.xcb_get_file_descriptor, ctypes.c_int, connection)
        self.get_setup = self._declare(library.xcb_get_setup, ctypes.c_void_p, connection)
        self.setup_roots_iterator = self._declare(library.xcb_setup_roots_iterator, ScreenIterator, ctypes.c_void_p)
        self.generate_id = self._declare(library.xcb_generate_id, ctypes.c_uint32, connection)
        self.create_window = self._declare(
            library.xcb_create_window,
            Cookie,
            connection,
            ctypes.c_uint8,
            window,
            window,
            ctypes.c_int16,
            ctypes.c_int16,
            ctypes.c_uint16,
            ctypes.c_uint16,
            ctypes.c_uint16,
            ctypes.c_uint16,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        )
        self.intern_atom = self._declare(
            library.xcb_intern_atom,
            Cookie,
            connection,
            ctypes.c_uint8,
            ctypes.c_uint16,
            ctypes.c_char_p,
        )
        self.intern_atom_reply = self._declare(
            library.xcb_intern_atom_reply,
            ctypes.POINTER(InternAtomReply),
            connection,
            Cookie,
            ctypes.c_void_p,
        )
        self.get_selection_owner = self._declare(library.xcb_get_selection_owner, Cookie, connection, atom)
        self.get_selection_owner_reply = self._declare(
            library.xcb_get_selection_owner_reply,
            ctypes.POINTER(SelectionOwnerReply),
            connection,
            Cookie,
            ctypes.c_void_p,
        )
        self.convert_selection = self._declare(
            library.xcb_convert_selection,
            Cookie,
            connection,
            window,
            atom,
            atom,
            atom,
            ctypes.c_uint32,
        )
        self.get_property = self._declare(
            library.xcb_get_property,
            Cookie,
            connection,
            ctypes.c_uint8,
            window,
            atom,
            atom,
            ctypes.c_uint32,
            ctypes.c_uint32,
        )
        self.get_property_reply = self._declare(
            library.xcb_get_property_reply,
            ctypes.POINTER(PropertyReply),
            connection,
            Cookie,
            ctypes.c_void_p,
        )
        self.get_property_value = self._declare(
            library.xcb_get_property_value,
            ctypes.c_void_p,
            ctypes.POINTER(PropertyReply),
        )
        self.get_property_value_length = self._declare(
            library.xcb_get_property_value_length,
            ctypes.c_int,
            ctypes.POINTER(PropertyReply),
        )
        self.poll_for_event = self._declare(library.xcb_poll_for_event, ctypes.POINTER(GenericEvent), connection)

    @staticmethod
    def _declare(function: Any, returns: Any, *takes: Any) -> Any:
        function.restype = returns
        function.argtypes = list(takes)
        return function


@cache
def load_xcb() -> Optional[XcbLibrary]:
    """libxcb, loaded once, while the system provides it."""
    try:
        library = ctypes.CDLL(XCB_LIBRARY)
    except OSError:
        return None

    return XcbLibrary(library)
