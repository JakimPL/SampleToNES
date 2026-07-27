from typing import Callable, List
from unittest.mock import patch

import pytest

from sampletones_application.utils.gui.keyboard import (
    PRIORITY_MODAL,
    PRIORITY_SHORTCUT,
    KeyEvent,
    KeyRouter,
    focus,
)
from sampletones_application.utils.gui.keyboard.modifiers import CTRL, NO_MODIFIERS

EVENT_MODULE = "sampletones_application.utils.gui.keyboard.event"


def _event() -> KeyEvent:
    return KeyEvent(key=1, modifiers=NO_MODIFIERS)


def _recorder(log: List[str], label: str, claims: bool) -> Callable[[KeyEvent], bool]:
    def handle(event: KeyEvent) -> bool:
        log.append(label)
        return claims

    return handle


def _capturing(received: List[KeyEvent]) -> Callable[[KeyEvent], bool]:
    def handle(event: KeyEvent) -> bool:
        received.append(event)
        return True

    return handle


class _RecordingModal:
    def __init__(self) -> None:
        self.keys: List[int] = []

    def handle_key(self, event: KeyEvent) -> None:
        self.keys.append(event.key)


class TestRouting:
    def test_higher_priority_scope_is_offered_first(self) -> None:
        router = KeyRouter()
        log: List[str] = []
        router.register(_recorder(log, "low", True), priority=PRIORITY_SHORTCUT, active=lambda: True)
        router.register(_recorder(log, "high", True), priority=PRIORITY_MODAL, active=lambda: True)

        router.route(_event())

        assert log == ["high"]

    def test_walk_continues_until_a_scope_claims(self) -> None:
        router = KeyRouter()
        log: List[str] = []
        router.register(_recorder(log, "high", False), priority=PRIORITY_MODAL, active=lambda: True)
        router.register(_recorder(log, "low", True), priority=PRIORITY_SHORTCUT, active=lambda: True)

        claimed = router.route(_event())

        assert claimed
        assert log == ["high", "low"]

    def test_inactive_scope_is_skipped(self) -> None:
        router = KeyRouter()
        log: List[str] = []
        router.register(_recorder(log, "inactive", True), priority=PRIORITY_MODAL, active=lambda: False)
        router.register(_recorder(log, "active", True), priority=PRIORITY_SHORTCUT, active=lambda: True)

        router.route(_event())

        assert log == ["active"]

    def test_unclaimed_event_reports_not_handled(self) -> None:
        router = KeyRouter()
        router.register(_recorder([], "declines", False), priority=PRIORITY_SHORTCUT, active=lambda: True)

        assert not router.route(_event())


class TestModal:
    def test_push_marks_modal_open(self) -> None:
        router = KeyRouter()

        router.push_modal(_RecordingModal())

        assert router.is_modal_open

    def test_nested_modals_stay_open_until_last_pop(self) -> None:
        router = KeyRouter()
        router.push_modal(_RecordingModal())
        router.push_modal(_RecordingModal())

        router.pop_modal()

        assert router.is_modal_open

    def test_pop_without_a_modal_stays_closed(self) -> None:
        router = KeyRouter()

        router.pop_modal()

        assert not router.is_modal_open

    def test_an_open_modal_claims_the_key_and_suppresses_lower_scopes(self) -> None:
        router = KeyRouter()
        log: List[str] = []
        router.register(_recorder(log, "shortcut", True), priority=PRIORITY_SHORTCUT, active=lambda: True)
        modal = _RecordingModal()
        router.push_modal(modal)

        claimed = router.route(_event())

        assert claimed
        assert log == []
        assert modal.keys == [_event().key]

    def test_the_topmost_modal_receives_the_key(self) -> None:
        router = KeyRouter()
        lower = _RecordingModal()
        upper = _RecordingModal()
        router.push_modal(lower)
        router.push_modal(upper)

        router.route(_event())

        assert upper.keys == [_event().key]
        assert lower.keys == []

    def test_a_closed_modal_returns_the_keyboard_to_lower_scopes(self) -> None:
        router = KeyRouter()
        log: List[str] = []
        router.register(_recorder(log, "shortcut", True), priority=PRIORITY_SHORTCUT, active=lambda: True)
        router.push_modal(_RecordingModal())
        router.pop_modal()

        claimed = router.route(_event())

        assert claimed
        assert log == ["shortcut"]


class TestDispatch:
    def test_dispatch_captures_the_modifiers_and_routes_the_event(self) -> None:
        router = KeyRouter()
        received: List[KeyEvent] = []
        router.register(_capturing(received), priority=PRIORITY_SHORTCUT, active=lambda: True)

        with patch(f"{EVENT_MODULE}.capture_modifiers", lambda: CTRL):
            router._dispatch("handler", 65)

        assert received == [KeyEvent(key=65, modifiers=CTRL)]


class TestFieldFocus:
    def test_field_focus_reflects_the_focus_query(self, monkeypatch: pytest.MonkeyPatch) -> None:
        router = KeyRouter()

        monkeypatch.setattr(focus, "is_field_focused", lambda: True)
        assert router.is_field_focused

        monkeypatch.setattr(focus, "is_field_focused", lambda: False)
        assert not router.is_field_focused
