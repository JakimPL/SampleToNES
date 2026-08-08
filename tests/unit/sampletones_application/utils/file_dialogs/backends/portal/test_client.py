from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Deque, Dict, Final, Iterator, List, Optional, Tuple, cast

import pytest
from jeepney import HeaderFields, MatchRule, MessageType

from sampletones_application.utils.file_dialogs.backends.portal import client as client_module
from sampletones_application.utils.file_dialogs.backends.portal.client import (
    NAME_OWNER_CHANGED_SIGNAL,
    NO_OWNER,
    PORTAL_BUS_NAME,
    RESPONSE_SIGNAL,
    FileChooserClient,
)
from sampletones_application.utils.file_dialogs.backends.portal.response import (
    ChooserResult,
)
from sampletones_application.utils.file_dialogs.backends.portal.variant import Variant

HANDLE: Final[str] = "/org/freedesktop/portal/desktop/request/1_42/sampletones"
OTHER_HANDLE: Final[str] = "/org/freedesktop/portal/desktop/request/1_7/elsewhere"
LABEL: Final[str] = "Bitphase instrument preset (*.json)"
PORTAL_OWNER: Final[str] = ":1.42"
PARENT_WINDOW: Final[str] = "x11:2200132"


def _message(
    body: Tuple[object, ...],
    path: Optional[str] = None,
    member: Optional[str] = None,
) -> SimpleNamespace:
    fields: Dict[HeaderFields, str] = {}
    if path is not None:
        fields[HeaderFields.path] = path
    if member is not None:
        fields[HeaderFields.member] = member

    return SimpleNamespace(
        header=SimpleNamespace(fields=fields, message_type=MessageType.method_return),
        body=body,
    )


def _response(
    code: int,
    results: Dict[str, Variant],
    path: str = HANDLE,
) -> SimpleNamespace:
    return _message(
        (code, results),
        path=path,
        member=RESPONSE_SIGNAL,
    )


def _name_owner_changed(
    previous_owner: str,
    current_owner: str,
) -> SimpleNamespace:
    return _message(
        (
            PORTAL_BUS_NAME,
            previous_owner,
            current_owner,
        ),
        member=NAME_OWNER_CHANGED_SIGNAL,
    )


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
        self.bodies: List[Tuple[object, ...]] = []
        self.rules: List[object] = []
        self.closed = False

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *arguments: object) -> None:
        self.closed = True

    @contextmanager
    def filter(
        self,
        rule: object,
        *,
        queue: Optional[Deque[SimpleNamespace]] = None,
    ) -> Iterator[Deque[SimpleNamespace]]:
        self.rules.append(rule)
        yield self._signals if queue is None else queue

    def send_and_get_reply(self, message: object) -> SimpleNamespace:
        member = getattr(message, "header").fields[HeaderFields.member]
        self.sent.append(member)
        self.bodies.append(getattr(message, "body"))
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
            replies=[_message(("ok",)), _message(("ok",)), _message((HANDLE,))],
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
        assert connection.sent == ["AddMatch", "AddMatch", "SaveFile"]

    def test_the_dialog_names_the_application_s_window_as_its_parent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The window a dialog belongs to is what the portal places it over."""
        connection = FakeConnection(
            replies=[_message(("ok",)), _message(("ok",)), _message((HANDLE,))],
            signals=[_response(1, {})],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))
        monkeypatch.setattr(client_module, "parent_window_handle", lambda: PARENT_WINDOW)

        FileChooserClient().call(method="SaveFile", title="Export instrument", options={})

        assert connection.bodies[-1] == (
            PARENT_WINDOW,
            "Export instrument",
            {},
        )

    def test_another_request_s_response_is_passed_over(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Every portal response on the bus reaches the subscription, so each call waits for its own."""
        connection = FakeConnection(
            replies=[_message(("ok",)), _message(("ok",)), _message((HANDLE,))],
            signals=[
                _response(
                    0,
                    {"uris": ("as", ["file:///elsewhere/other.json"])},
                    path=OTHER_HANDLE,
                ),
                _response(0, {"uris": ("as", ["file:///home/user/kick.json"])}),
            ],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        result = FileChooserClient().call(method="SaveFile", title="Export instrument", options={})

        assert result == ChooserResult(uris=("file:///home/user/kick.json",), filter_label=None)

    def test_a_dismissed_dialog_answers_with_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connection = FakeConnection(
            replies=[_message(("ok",)), _message(("ok",)), _message((HANDLE,))],
            signals=[_response(1, {})],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        assert FileChooserClient().call(method="SaveFile", title="Export instrument", options={}) is None


class TestAPortalLeavingTheBus:
    """The portal owes every open dialog its response, so the bus announcing that name released
    is what tells a waiting call the answer is never coming."""

    def test_the_call_subscribes_to_the_portal_s_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connection = FakeConnection(
            replies=[_message(("ok",)), _message(("ok",)), _message((HANDLE,))],
            signals=[_response(1, {})],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        FileChooserClient().call(method="SaveFile", title="Export instrument", options={})

        subscriptions = [cast(MatchRule, rule).serialise() for rule in connection.rules]
        assert any(NAME_OWNER_CHANGED_SIGNAL in rule and PORTAL_BUS_NAME in rule for rule in subscriptions)

    def test_the_name_released_ends_the_wait(self, monkeypatch: pytest.MonkeyPatch) -> None:
        connection = FakeConnection(
            replies=[_message(("ok",)), _message(("ok",)), _message((HANDLE,))],
            signals=[_name_owner_changed(PORTAL_OWNER, NO_OWNER)],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        assert FileChooserClient().call(method="SaveFile", title="Export instrument", options={}) is None

    def test_the_name_taken_up_leaves_the_dialog_waiting(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A call may be what starts the portal, so the name arriving is the dialog opening."""
        connection = FakeConnection(
            replies=[_message(("ok",)), _message(("ok",)), _message((HANDLE,))],
            signals=[
                _name_owner_changed(NO_OWNER, PORTAL_OWNER),
                _response(0, {"uris": ("as", ["file:///home/user/kick.json"])}),
            ],
        )
        monkeypatch.setattr(client_module, "open_dbus_connection", _connecting(connection))

        result = FileChooserClient().call(method="SaveFile", title="Export instrument", options={})

        assert result == ChooserResult(uris=("file:///home/user/kick.json",), filter_label=None)
