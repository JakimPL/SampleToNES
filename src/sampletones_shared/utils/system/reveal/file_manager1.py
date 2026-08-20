from pathlib import Path
from typing import Final, List, Tuple, Type

from jeepney import (
    AuthenticationError,
    DBusAddress,
    DBusErrorResponse,
    new_method_call,
)
from jeepney.io.blocking import open_dbus_connection

FILE_MANAGER_BUS_NAME: Final[str] = "org.freedesktop.FileManager1"
FILE_MANAGER_OBJECT_PATH: Final[str] = "/org/freedesktop/FileManager1"
FILE_MANAGER_INTERFACE: Final[str] = "org.freedesktop.FileManager1"
SHOW_ITEMS_METHOD: Final[str] = "ShowItems"
SHOW_ITEMS_SIGNATURE: Final[str] = "ass"
EMPTY_STARTUP_ID: Final[str] = ""
SESSION_BUS: Final[str] = "SESSION"

FILE_MANAGER_ADDRESS: Final[DBusAddress] = DBusAddress(
    FILE_MANAGER_OBJECT_PATH,
    bus_name=FILE_MANAGER_BUS_NAME,
    interface=FILE_MANAGER_INTERFACE,
)

OUT_OF_REACH_ERRORS: Final[Tuple[Type[Exception], ...]] = (
    KeyError,
    RuntimeError,
    OSError,
    AuthenticationError,
    DBusErrorResponse,
)


class FileManager1Backend:
    """
    Reveals files through the desktop's ``org.freedesktop.FileManager1`` service.

    One ``ShowItems`` call opens a single file-manager window with every file selected,
    whichever directories the files live in. The method takes the file URIs followed by a
    startup id; an empty startup id marks the call as independent of any launch context,
    which file managers accept.
    """

    def open(self, paths: Tuple[Path, ...]) -> None:
        uris: List[str] = [path.as_uri() for path in paths]
        with open_dbus_connection(bus=SESSION_BUS) as connection:
            connection.send_and_get_reply(
                new_method_call(
                    FILE_MANAGER_ADDRESS,
                    SHOW_ITEMS_METHOD,
                    SHOW_ITEMS_SIGNATURE,
                    (uris, EMPTY_STARTUP_ID),
                )
            )

    @classmethod
    def answers(cls) -> bool:
        """
        Reports whether the service answers a probe call on the session bus.

        The probe sends ``ShowItems`` with an empty URI list, which the service answers once
        it accepts the interface. ``open_dbus_connection`` opens the session bus directly, so
        the probe reaches the same service :meth:`open` uses.
        """
        try:
            with open_dbus_connection(bus=SESSION_BUS) as connection:
                connection.send_and_get_reply(
                    new_method_call(
                        FILE_MANAGER_ADDRESS,
                        SHOW_ITEMS_METHOD,
                        SHOW_ITEMS_SIGNATURE,
                        ([], EMPTY_STARTUP_ID),
                    )
                )
        except OUT_OF_REACH_ERRORS:
            return False

        return True
