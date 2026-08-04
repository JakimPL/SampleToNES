import ctypes
import os
from ctypes import CDLL, POINTER, byref, c_char_p, c_int, c_long, c_ubyte, c_ulong, c_void_p
from typing import Final, List, Optional, Self

X11_LIBRARY: Final[str] = "libX11.so.6"

CLIENT_LIST_PROPERTY: Final[bytes] = b"_NET_CLIENT_LIST"
PROCESS_PROPERTY: Final[bytes] = b"_NET_WM_PID"

WINDOW_ATOM: Final[int] = 33
CARDINAL_ATOM: Final[int] = 6

NO_ATOM: Final[int] = 0
PROPERTY_READ: Final[int] = 0

PROPERTY_OFFSET: Final[int] = 0
PROPERTY_WORD_LIMIT: Final[int] = 1024

ATOM_MUST_EXIST: Final[bool] = True
KEEP_PROPERTY: Final[bool] = False

X11_HANDLE_PREFIX: Final[str] = "x11:"
NO_PARENT_WINDOW: Final[str] = ""


class X11Display:
    """
    A connection to the X server, opened to read the windows an X11 desktop manages.

    The desktop lists the windows it manages on the root window and each listed window carries
    the process that owns it, so an application finds its own window by the process it runs as.
    A connection holds a socket to the server for as long as it stays open, which ``close``
    releases once a lookup is done with it.
    """

    def __init__(
        self,
        library: CDLL,
        display: int,
    ) -> None:
        self._library = library
        self._display = display

    @classmethod
    def open(cls) -> Optional[Self]:
        """
        Opens the display the environment names.

        Returns:
            Optional[Self]: The open connection, ``None`` where libX11 is out of reach or the
                environment names no server, which is how a session running without X11 answers.
        """
        try:
            library = CDLL(X11_LIBRARY)
        except OSError:
            return None

        cls._declare_signatures(library)
        display = library.XOpenDisplay(None)
        if not display:
            return None

        return cls(library, display)

    def close(self) -> None:
        """Releases the connection to the server."""
        self._library.XCloseDisplay(self._display)

    def window_of_process(self, process_id: int) -> Optional[int]:
        """
        Returns the identifier of the window the desktop manages for a process.

        The window list and the process owning a window are properties the X server gives types
        of its own, which a read names by the atoms those types are known under.

        Args:
            process_id: The process whose window to look for.

        Returns:
            Optional[int]: The first listed window that process owns, ``None`` where the desktop
                lists none for it.
        """
        root = self._library.XDefaultRootWindow(self._display)
        for window in self._numbers(root, CLIENT_LIST_PROPERTY, WINDOW_ATOM):
            if process_id in self._numbers(window, PROCESS_PROPERTY, CARDINAL_ATOM):
                return window

        return None

    def _numbers(
        self,
        window: int,
        name: bytes,
        value_type: int,
    ) -> List[int]:
        """
        The numbers a window's property holds, empty for a window carrying no such property.

        The server reports what it read through the values passed by reference, and owns the
        array it answers with until ``XFree`` releases it. A property of the 32-bit format
        arrives as an array of C longs, which is what its values are read as, and one read takes
        as many of those words as a desktop's window list needs.
        """
        atom = self._library.XInternAtom(self._display, name, ATOM_MUST_EXIST)
        if atom == NO_ATOM:
            return []

        type_read = c_ulong(0)
        format_read = c_int(0)
        items_read = c_ulong(0)
        remaining = c_ulong(0)
        values = POINTER(c_ubyte)()
        status = self._library.XGetWindowProperty(
            self._display,
            window,
            atom,
            PROPERTY_OFFSET,
            PROPERTY_WORD_LIMIT,
            KEEP_PROPERTY,
            value_type,
            byref(type_read),
            byref(format_read),
            byref(items_read),
            byref(remaining),
            byref(values),
        )
        if status != PROPERTY_READ or not values:
            return []

        try:
            numbers = ctypes.cast(values, POINTER(c_ulong))
            return [int(numbers[index]) for index in range(items_read.value)]
        finally:
            self._library.XFree(values)

    @staticmethod
    def _declare_signatures(library: CDLL) -> None:
        """The types of the libX11 calls a lookup makes, which ctypes reads to marshal them."""
        library.XOpenDisplay.argtypes = [c_char_p]
        library.XOpenDisplay.restype = c_void_p
        library.XCloseDisplay.argtypes = [c_void_p]
        library.XCloseDisplay.restype = c_int
        library.XDefaultRootWindow.argtypes = [c_void_p]
        library.XDefaultRootWindow.restype = c_ulong
        library.XInternAtom.argtypes = [c_void_p, c_char_p, c_int]
        library.XInternAtom.restype = c_ulong
        library.XGetWindowProperty.argtypes = [
            c_void_p,
            c_ulong,
            c_ulong,
            c_long,
            c_long,
            c_int,
            c_ulong,
            POINTER(c_ulong),
            POINTER(c_int),
            POINTER(c_ulong),
            POINTER(c_ulong),
            POINTER(POINTER(c_ubyte)),
        ]
        library.XGetWindowProperty.restype = c_int
        library.XFree.argtypes = [c_void_p]
        library.XFree.restype = c_int


def parent_window_handle() -> str:
    """
    Returns the handle naming the window a portal dialog belongs to.

    The portal gives a dialog the window that asked for it as its parent, which is what keeps
    the dialog above that window and lets the desktop place it there. An X11 desktop names a
    window by its identifier written in hexadecimal.

    Returns:
        str: The handle naming this application's window, empty where the session names no such
            window, which asks the portal for a dialog standing on its own.
    """
    display = X11Display.open()
    if display is None:
        return NO_PARENT_WINDOW

    try:
        window_id = display.window_of_process(os.getpid())
    finally:
        display.close()

    if window_id is None:
        return NO_PARENT_WINDOW

    return f"{X11_HANDLE_PREFIX}{window_id:x}"
