from pathlib import Path
from unittest.mock import MagicMock, patch

from jeepney import (
    AuthenticationError,
    DBusErrorResponse,
    Endianness,
    HeaderFields,
    MessageFlag,
    MessageType,
)
from jeepney.low_level import Header, Message

from sampletones_shared.utils.system.reveal.file_manager1 import (
    EMPTY_STARTUP_ID,
    FILE_MANAGER_ADDRESS,
    SHOW_ITEMS_METHOD,
    SHOW_ITEMS_SIGNATURE,
    FileManager1Backend,
)

MODULE = "sampletones_shared.utils.system.reveal.file_manager1"
METHOD_UNKNOWN_ERROR: str = "org.freedesktop.FileManager1.MethodUnknown"


def _error_response() -> DBusErrorResponse:
    header = Header(
        Endianness.little,
        MessageType.error,
        MessageFlag.no_reply_expected,
        1,
        0,
        0,
        {HeaderFields.error_name: METHOD_UNKNOWN_ERROR},
    )
    return DBusErrorResponse(Message(header, ()))


class TestOpen:
    def test_sends_one_show_items_call_with_every_uri(self) -> None:
        paths = (
            Path("/a/one.wav"),
            Path("/b/two.wav"),
        )

        with patch(f"{MODULE}.open_dbus_connection") as open_connection:
            connection = MagicMock()
            open_connection.return_value.__enter__.return_value = connection
            with patch(f"{MODULE}.new_method_call") as build_call:
                FileManager1Backend().open(paths)

        build_call.assert_called_once_with(
            FILE_MANAGER_ADDRESS,
            SHOW_ITEMS_METHOD,
            SHOW_ITEMS_SIGNATURE,
            ([Path("/a/one.wav").as_uri(), Path("/b/two.wav").as_uri()], EMPTY_STARTUP_ID),
        )
        connection.send_and_get_reply.assert_called_once_with(build_call.return_value)


class TestAnswers:
    def test_an_answered_probe_reports_true(self) -> None:
        with patch(f"{MODULE}.open_dbus_connection") as open_connection:
            assert FileManager1Backend.answers()

        open_connection.assert_called_once_with(bus="SESSION")

    @patch(f"{MODULE}.open_dbus_connection", side_effect=_error_response())
    def test_an_erroring_probe_reports_false(self, open_connection: MagicMock) -> None:
        assert not FileManager1Backend.answers()

    @patch(f"{MODULE}.open_dbus_connection", side_effect=AuthenticationError("denied"))
    def test_an_unreachable_bus_reports_false(self, open_connection: MagicMock) -> None:
        assert not FileManager1Backend.answers()
