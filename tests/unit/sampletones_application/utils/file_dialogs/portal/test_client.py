from collections import deque
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Deque, Dict, Final, Iterator, List, Optional, Tuple

import pytest
from jeepney import HeaderFields, MessageType

from sampletones_application.utils.file_dialogs.portal import client as client_module
from sampletones_application.utils.file_dialogs.portal.client import (
    ChooserResult,
    FileChooserClient,
    Variant,
)

HANDLE: Final[str] = "/org/freedesktop/portal/desktop/request/1_42/sampletones"
OTHER_HANDLE: Final[str] = "/org/freedesktop/portal/desktop/request/1_7/elsewhere"
LABEL: Final[str] = "Bitphase instrument preset (*.json)"


def _message(
    body: Tuple[object, ...],
    path: Optional[str] = None,
) -> SimpleNamespace:
    fields: Dict[HeaderFields, str] = {} if path is None else {HeaderFields.path: path}
    return SimpleNamespace(
        header=SimpleNamespace(fields=fields, message_type=MessageType.method_return),
        body=body,
    )


def _response(
    code: int,
    results: Dict[str, Variant],
    path: str = HANDLE,
) -> SimpleNamespace:
    return _message((code, results), path=path)


class FakeConnection:
    """A session bus answering method calls in order and delivering prepared signals."""

    def __init__(
        self,
        replies: List[SimpleNamespace],
        signals: List[SimpleNamespace],
    ) -> None:
        self._replies = deque(replies)
        self._signals = deque(signals)
        self.sent: List[str] = []
        self.rules: List[object] = []
        self.closed = False

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *arguments: object) -> None:
        self.closed = True

    @contextmanager
    def filter(self, rule: object) -> Iterator[Deque[SimpleNamespace]]:
        self.rules.append(rule)
        yield self._signals

    def send_and_get_reply(self, message: object) -> SimpleNamespace:
        member = getattr(message, "header").fields[HeaderFields.member]
        self.sent.append(member)
        return self._replies.popleft()

    def recv_until_filtered(self, queue: Deque[SimpleNamespace]) -> SimpleNamespace:
        return queue.popleft()


def _connecting(connection: FakeConnection) -> object:
    def opener(*, bus: str) -> FakeConnection:
        assert bus == "SESSION"
        return connection

    return opener


class TestVersion:
    def test_the_portal_reports_the_interface_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connection = FakeConnection(replies=[_message((("u", 3),))], signals=[])
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        assert FileChooserClient().version() == 3
        assert connection.closed

    @pytest.mark.parametrize(
        "failure",
        [
            KeyError("DBUS_SESSION_BUS_ADDRESS"),
            FileNotFoundError("no such socket"),
            RuntimeError("unsupported transport"),
        ],
    )
    def test_a_bus_out_of_reach_leaves_the_version_unknown(
        self,
        monkeypatch: pytest.MonkeyPatch,
        failure: Exception,
    ) -> None:
        def opener(*, bus: str) -> FakeConnection:
            raise failure

        monkeypatch.setattr(client_module, "open_dbus_connection", opener)

        assert FileChooserClient().version() is None


class TestCall:
    def test_the_response_to_the_open_request_is_the_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connection = FakeConnection(
            replies=[_message(("ok",)), _message((HANDLE,))],
            signals=[
                _response(
                    0,
                    {
                        "uris": ("as", ["file:///home/user/kick.json"]),
                        "current_filter": ("(sa(us))", (LABEL, [(0, "*.json")])),
                    },
                )
            ],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        result = FileChooserClient().call(method="SaveFile", title="Export instrument", options={})

        assert result == ChooserResult(uris=("file:///home/user/kick.json",), filter_label=LABEL)
        assert connection.sent == ["AddMatch", "SaveFile"]

    def test_another_request_s_response_is_passed_over(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Every portal response on the bus reaches the subscription, so each call waits for its own."""
        connection = FakeConnection(
            replies=[_message(("ok",)), _message((HANDLE,))],
            signals=[
                _response(0, {"uris": ("as", ["file:///elsewhere/other.json"])}, path=OTHER_HANDLE),
                _response(0, {"uris": ("as", ["file:///home/user/kick.json"])}),
            ],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        result = FileChooserClient().call(method="SaveFile", title="Export instrument", options={})

        assert result == ChooserResult(uris=("file:///home/user/kick.json",), filter_label=None)

    def test_a_dismissed_dialog_answers_with_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connection = FakeConnection(
            replies=[_message(("ok",)), _message((HANDLE,))],
            signals=[_response(1, {})],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        assert FileChooserClient().call(method="SaveFile", title="Export instrument", options={}) is None
