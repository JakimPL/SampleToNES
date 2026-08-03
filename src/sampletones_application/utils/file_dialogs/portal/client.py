from dataclasses import dataclass
from typing import Dict, Final, List, Optional, Tuple, Type, cast

from jeepney import (
    AuthenticationError,
    DBusAddress,
    DBusErrorResponse,
    HeaderFields,
    MatchRule,
    Properties,
    message_bus,
    new_method_call,
)
from jeepney.io.blocking import open_dbus_connection, unwrap_msg
from jeepney.low_level import Message

Variant = Tuple[str, object]
"""A D-Bus variant as jeepney represents it: the value's signature, then the value."""

SESSION_BUS: Final[str] = "SESSION"
PORTAL_BUS_NAME: Final[str] = "org.freedesktop.portal.Desktop"
PORTAL_OBJECT_PATH: Final[str] = "/org/freedesktop/portal/desktop"
FILE_CHOOSER_INTERFACE: Final[str] = "org.freedesktop.portal.FileChooser"
REQUEST_INTERFACE: Final[str] = "org.freedesktop.portal.Request"
RESPONSE_SIGNAL: Final[str] = "Response"
VERSION_PROPERTY: Final[str] = "version"

CALL_SIGNATURE: Final[str] = "ssa{sv}"
PARENT_WINDOW: Final[str] = ""
URIS_RESULT: Final[str] = "uris"
CURRENT_FILTER_RESULT: Final[str] = "current_filter"
SUCCESS_CODE: Final[int] = 0

PORTAL_OUT_OF_REACH_ERRORS: Final[Tuple[Type[Exception], ...]] = (
    KeyError,  # the session bus address is absent from the environment
    RuntimeError,  # the address names a transport jeepney speaks no dialect of
    OSError,  # the socket the address names refused the connection
    AuthenticationError,
    DBusErrorResponse,  # the bus answers, and no portal claims the interface
)

FILE_CHOOSER: Final[DBusAddress] = DBusAddress(
    PORTAL_OBJECT_PATH,
    bus_name=PORTAL_BUS_NAME,
    interface=FILE_CHOOSER_INTERFACE,
)


@dataclass(frozen=True)
class ChooserResult:
    """
    What a file-chooser dialog answered with.

    ``uris`` carries the chosen locations in the dialog's own order. ``filter_label`` is the
    label of the type its selector stood on, present for a portal implementation that reports
    the selection.
    """

    uris: Tuple[str, ...]
    filter_label: Optional[str]


class FileChooserClient:
    """
    The desktop portal's ``FileChooser`` interface, reached over the session bus.

    A call asks the portal for a dialog and answers once the user closes it. The portal replies
    to the call with the object path of a request and delivers the outcome as a signal on that
    path, so each call subscribes to the signal before asking and then waits for the response
    belonging to its own request. Every dialog runs in the desktop's own portal implementation,
    which is what makes the file-type selector and the type it reports available at all.
    """

    def version(self) -> Optional[int]:
        """
        Returns the ``FileChooser`` version the portal on the session bus implements.

        Answers ``None`` where the session bus is out of reach or no portal claims the
        interface, which is the environment's way of saying dialogs belong to another backend.
        """
        try:
            with open_dbus_connection(bus=SESSION_BUS) as connection:
                reply = connection.send_and_get_reply(Properties(FILE_CHOOSER).get(VERSION_PROPERTY))
                (version,) = cast(Tuple[Variant], unwrap_msg(reply))
        except PORTAL_OUT_OF_REACH_ERRORS:
            return None

        return cast(int, version[1])

    def call(
        self,
        *,
        method: str,
        title: str,
        options: Dict[str, Variant],
    ) -> Optional[ChooserResult]:
        """
        Opens the dialog ``method`` names and waits for the user to answer it.

        Args:
            method: The ``FileChooser`` method to call, naming the kind of dialog to open.
            title: The window title the dialog carries.
            options: The portal options for that method, each value a D-Bus variant.

        Returns:
            Optional[ChooserResult]: What the dialog answered, or ``None`` once it was dismissed.
        """
        rule = MatchRule(
            type="signal",
            interface=REQUEST_INTERFACE,
            member=RESPONSE_SIGNAL,
        )
        request = new_method_call(
            FILE_CHOOSER,
            method,
            CALL_SIGNATURE,
            (
                PARENT_WINDOW,
                title,
                options,
            ),
        )

        with open_dbus_connection(bus=SESSION_BUS) as connection:
            with connection.filter(rule) as responses:
                connection.send_and_get_reply(message_bus.AddMatch(rule))
                (handle,) = cast(Tuple[str], unwrap_msg(connection.send_and_get_reply(request)))
                while True:
                    response = connection.recv_until_filtered(responses)
                    if _signal_path(response) == handle:
                        return _read_response(response)


def _read_response(response: Message) -> Optional[ChooserResult]:
    code, results = cast(Tuple[int, Dict[str, Variant]], response.body)
    if code != SUCCESS_CODE:
        return None

    return ChooserResult(
        uris=_uris(results),
        filter_label=_filter_label(results),
    )


def _uris(results: Dict[str, Variant]) -> Tuple[str, ...]:
    uris = results.get(URIS_RESULT)
    if uris is None:
        return ()

    return tuple(cast(List[str], uris[1]))


def _filter_label(results: Dict[str, Variant]) -> Optional[str]:
    """The label of the type the dialog stood on, as the portal reports the whole filter back."""
    reported = results.get(CURRENT_FILTER_RESULT)
    if reported is None:
        return None

    label, _patterns = cast(Tuple[str, List[Tuple[int, str]]], reported[1])
    return label


def _signal_path(response: Message) -> Optional[str]:
    return cast(Optional[str], response.header.fields.get(HeaderFields.path))
