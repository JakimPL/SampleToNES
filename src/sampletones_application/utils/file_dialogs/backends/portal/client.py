from typing import Deque, Dict, Final, Optional, Tuple, Type, cast

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
from jeepney.io.blocking import DBusConnection, open_dbus_connection, unwrap_msg
from jeepney.low_level import Message

from sampletones_application.utils.file_dialogs.backends.portal.parent import parent_window_handle
from sampletones_application.utils.file_dialogs.backends.portal.response import ChooserResult
from sampletones_application.utils.file_dialogs.backends.portal.variant import Variant

SESSION_BUS: Final[str] = "SESSION"
PORTAL_BUS_NAME: Final[str] = "org.freedesktop.portal.Desktop"
PORTAL_OBJECT_PATH: Final[str] = "/org/freedesktop/portal/desktop"
FILE_CHOOSER_INTERFACE: Final[str] = "org.freedesktop.portal.FileChooser"
REQUEST_INTERFACE: Final[str] = "org.freedesktop.portal.Request"
BUS_INTERFACE: Final[str] = "org.freedesktop.DBus"
RESPONSE_SIGNAL: Final[str] = "Response"
NAME_OWNER_CHANGED_SIGNAL: Final[str] = "NameOwnerChanged"
VERSION_PROPERTY: Final[str] = "version"

CALL_SIGNATURE: Final[str] = "ssa{sv}"
BUS_NAME_ARGUMENT: Final[int] = 0
NO_OWNER: Final[str] = ""

PORTAL_OUT_OF_REACH_ERRORS: Final[Tuple[Type[Exception], ...]] = (
    KeyError,
    RuntimeError,
    OSError,
    AuthenticationError,
    DBusErrorResponse,
)

FILE_CHOOSER: Final[DBusAddress] = DBusAddress(
    PORTAL_OBJECT_PATH,
    bus_name=PORTAL_BUS_NAME,
    interface=FILE_CHOOSER_INTERFACE,
)


class FileChooserClient:
    """
    The desktop portal's ``FileChooser`` interface, reached over the session bus.

    A call asks the portal for a dialog and answers once the user closes it. The portal replies
    to the call with the object path of a request and delivers the outcome as a signal on that
    path, so each call subscribes to the signal before asking and then waits for the response
    belonging to its own request. The same subscription covers the bus announcing who owns the
    portal's name, which is what tells a waiting call that the portal it is waiting on left.
    Every dialog runs in the desktop's own portal implementation, which is what makes the
    file-type selector and the type it reports available at all.
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

        The call names this application's window as the dialog's parent, which is what places
        the dialog over the window it was asked from.

        Args:
            method: The ``FileChooser`` method to call, naming the kind of dialog to open.
            title: The window title the dialog carries.
            options: The portal options for that method, each value a D-Bus variant.

        Returns:
            Optional[ChooserResult]: What the dialog answered, ``None`` once it was dismissed or
                once the portal drawing it left the bus.
        """
        response_rule = self._response_rule()
        owner_rule = self._portal_owner_rule()
        request = new_method_call(
            FILE_CHOOSER,
            method,
            CALL_SIGNATURE,
            (
                parent_window_handle(),
                title,
                options,
            ),
        )

        with open_dbus_connection(bus=SESSION_BUS) as connection:
            with connection.filter(response_rule) as signals, connection.filter(owner_rule, queue=signals):
                connection.send_and_get_reply(message_bus.AddMatch(response_rule))
                connection.send_and_get_reply(message_bus.AddMatch(owner_rule))
                (handle,) = cast(Tuple[str], unwrap_msg(connection.send_and_get_reply(request)))
                return self._answer(
                    connection,
                    signals,
                    handle,
                )

    @staticmethod
    def _response_rule() -> MatchRule:
        """Subscribes to the outcome of every portal request, each call recognising its own."""
        return MatchRule(
            type="signal",
            interface=REQUEST_INTERFACE,
            member=RESPONSE_SIGNAL,
        )

    @staticmethod
    def _portal_owner_rule() -> MatchRule:
        """Subscribes to the bus announcing the portal's name changing hands."""
        rule = MatchRule(
            type="signal",
            interface=BUS_INTERFACE,
            member=NAME_OWNER_CHANGED_SIGNAL,
        )
        rule.add_arg_condition(BUS_NAME_ARGUMENT, PORTAL_BUS_NAME)
        return rule

    @classmethod
    def _answer(
        cls,
        connection: DBusConnection,
        signals: Deque[Message],
        handle: str,
    ) -> Optional[ChooserResult]:
        """
        Waits for the request ``handle`` to answer, or for the portal owing that answer to leave.

        A dialog stands open for as long as the user takes over it, so the wait runs to the user's
        own pace. What bounds it instead is the portal: the bus announces the name being released,
        and a released name means the dialog on screen went with the process that drew it, leaving
        a request that answers to nobody. That ends the wait the way a dismissal does, since either
        way the user named no destination.
        """
        while True:
            signal = connection.recv_until_filtered(signals)
            if cls._portal_left_the_bus(signal):
                return None

            if cls._signal_path(signal) == handle:
                return ChooserResult.from_response(signal)

    @classmethod
    def _portal_left_the_bus(cls, signal: Message) -> bool:
        if cls._signal_member(signal) != NAME_OWNER_CHANGED_SIGNAL:
            return False

        _name, _previous_owner, current_owner = cast(Tuple[str, str, str], signal.body)
        return current_owner == NO_OWNER

    @staticmethod
    def _signal_path(signal: Message) -> Optional[str]:
        return cast(Optional[str], signal.header.fields.get(HeaderFields.path))

    @staticmethod
    def _signal_member(signal: Message) -> Optional[str]:
        return cast(Optional[str], signal.header.fields.get(HeaderFields.member))
