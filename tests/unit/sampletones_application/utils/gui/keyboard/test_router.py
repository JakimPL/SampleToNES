from typing import Callable, Final, List
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard import (
    PRIORITY_MODAL,
    PRIORITY_PANEL,
    PRIORITY_SHORTCUT,
    KeyEvent,
    KeyRouter,
    focus,
)
from sampletones_application.utils.gui.keyboard.modifiers import CTRL, NO_MODIFIERS

EVENT_MODULE = "sampletones_application.utils.gui.keyboard.event"
PIANO_KEY: Final[int] = 90
OTHER_KEY: Final[int] = 83


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
        router.register(
            _recorder(log, "inactive", True),
            priority=PRIORITY_MODAL,
            active=lambda: False,
        )
        router.register(
            _recorder(log, "active", True),
            priority=PRIORITY_SHORTCUT,
            active=lambda: True,
        )

        router.route(_event())

        assert log == ["active"]

    def test_unclaimed_event_reports_not_handled(self) -> None:
        router = KeyRouter()
        router.register(
            _recorder([], "declines", False),
            priority=PRIORITY_SHORTCUT,
            active=lambda: True,
        )

        assert not router.route(_event())


class TestModal:
    def test_push_marks_modal_open(self) -> None:
        router = KeyRouter()

        router.push_modal(_RecordingModal())

        assert router.is_modal_open

    def test_nested_modals_stay_open_until_last_pop(self) -> None:
        router = KeyRouter()
        lower = _RecordingModal()
        upper = _RecordingModal()
        router.push_modal(lower)
        router.push_modal(upper)

        router.pop_modal(upper)

        assert router.is_modal_open

    def test_pop_without_a_modal_stays_closed(self) -> None:
        router = KeyRouter()

        router.pop_modal(_RecordingModal())

        assert not router.is_modal_open

    def test_a_claim_released_beneath_the_top_leaves_the_top_answering(self) -> None:
        """A dialog closing while a later one stands gives up its own claim and none other."""
        router = KeyRouter()
        lower = _RecordingModal()
        upper = _RecordingModal()
        router.push_modal(lower)
        router.push_modal(upper)

        router.pop_modal(lower)
        router.route(_event())

        assert upper.keys == [_event().key]
        assert lower.keys == []

    def test_a_claim_released_beneath_the_top_is_gone(self) -> None:
        router = KeyRouter()
        lower = _RecordingModal()
        upper = _RecordingModal()
        router.push_modal(lower)
        router.push_modal(upper)

        router.pop_modal(lower)
        router.pop_modal(upper)

        assert not router.is_modal_open

    def test_releasing_a_handler_holding_no_claim_changes_nothing(self) -> None:
        router = KeyRouter()
        standing = _RecordingModal()
        router.push_modal(standing)

        router.pop_modal(_RecordingModal())
        router.route(_event())

        assert standing.keys == [_event().key]

    def test_a_handler_claiming_twice_gives_up_one_claim_at_a_time(self) -> None:
        router = KeyRouter()
        handler = _RecordingModal()
        router.push_modal(handler)
        router.push_modal(handler)

        router.pop_modal(handler)

        assert router.is_modal_open

    def test_a_handler_claiming_twice_gives_up_its_latest_claim(self) -> None:
        """The claim released is the one standing highest, so what it stood above answers again."""
        router = KeyRouter()
        handler = _RecordingModal()
        other = _RecordingModal()
        router.push_modal(handler)
        router.push_modal(other)
        router.push_modal(handler)

        router.pop_modal(handler)
        router.route(_event())

        assert other.keys == [_event().key]

    def test_an_open_modal_claims_the_key_and_suppresses_lower_scopes(self) -> None:
        router = KeyRouter()
        log: List[str] = []
        router.register(
            _recorder(log, "shortcut", True),
            priority=PRIORITY_SHORTCUT,
            active=lambda: True,
        )
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
        router.register(
            _recorder(log, "shortcut", True),
            priority=PRIORITY_SHORTCUT,
            active=lambda: True,
        )
        modal = _RecordingModal()
        router.push_modal(modal)
        router.pop_modal(modal)

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


class _Holder:
    """A scope holding the keys it claims, as a key sounding a note does, keeping each press and release."""

    def __init__(self, *, claims: bool) -> None:
        self.claims = claims
        self.active = True
        self.presses: List[int] = []
        self.releases: List[int] = []

    def press(self, event: KeyEvent) -> bool:
        if self.claims:
            self.presses.append(event.key)

        return self.claims

    def release(self, key: int) -> None:
        self.releases.append(key)

    def register(self, router: KeyRouter, *, priority: int) -> None:
        router.register_holding(self.press, self.release, priority=priority, active=lambda: self.active)


def _key(key: int) -> KeyEvent:
    return KeyEvent(key=key, modifiers=NO_MODIFIERS)


class TestHeldKeys:
    """A scope holding its keys takes their releases, hears no repeat, and lets go of a key found up."""

    def test_a_held_key_lifted_reaches_the_scope_that_took_it(self) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)

        router.route(_key(PIANO_KEY))
        router.release(PIANO_KEY)

        assert holder.releases == [PIANO_KEY]

    def test_a_held_key_lifted_after_its_scope_went_inactive_still_reaches_it(self) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))

        holder.active = False
        router.release(PIANO_KEY)

        assert holder.releases == [PIANO_KEY]

    def test_a_held_key_lifted_under_a_modal_still_reaches_its_scope(self) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))
        modal = _RecordingModal()

        router.push_modal(modal)
        router.release(PIANO_KEY)

        assert holder.releases == [PIANO_KEY]
        assert modal.keys == []

    def test_a_repeat_of_a_held_key_reaches_no_scope(self) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))

        repeated = router.route(_key(PIANO_KEY))
        router.release(PIANO_KEY)
        router.route(_key(PIANO_KEY))

        assert repeated
        assert holder.presses == [PIANO_KEY, PIANO_KEY]

    def test_a_repeat_reaches_a_scope_holding_nothing(self) -> None:
        router = KeyRouter()
        log: List[str] = []
        router.register(_recorder(log, "navigation", True), priority=PRIORITY_SHORTCUT, active=lambda: True)

        router.route(_key(PIANO_KEY))
        router.route(_key(PIANO_KEY))

        assert log == ["navigation", "navigation"]

    def test_a_press_the_holding_scope_declines_holds_nothing(self) -> None:
        router = KeyRouter()
        holder = _Holder(claims=False)
        holder.register(router, priority=PRIORITY_PANEL)
        log: List[str] = []
        router.register(_recorder(log, "shortcut", True), priority=PRIORITY_SHORTCUT, active=lambda: True)

        router.route(_key(PIANO_KEY))
        router.release(PIANO_KEY)

        assert holder.releases == []
        assert log == ["shortcut"]

    def test_a_release_of_a_key_nobody_holds_reaches_no_scope(self) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))

        router.release(OTHER_KEY)

        assert holder.releases == []
        router.release(PIANO_KEY)
        assert holder.releases == [PIANO_KEY]

    def test_a_key_released_twice_is_lifted_once(self) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))

        router.release(PIANO_KEY)
        router.release(PIANO_KEY)

        assert holder.releases == [PIANO_KEY]

    def test_the_release_handler_reaches_the_scope_holding_the_key(self) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))

        router._dispatch_release("handler", PIANO_KEY)

        assert holder.releases == [PIANO_KEY]


class TestTheSweep:
    """A held key the window no longer reports down is let go, as when the window lost focus while it was down."""

    def test_a_held_key_found_up_is_released(self, monkeypatch: pytest.MonkeyPatch) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))
        monkeypatch.setattr(dpg, "is_key_down", lambda key: False)

        router.sweep()

        assert holder.releases == [PIANO_KEY]

    def test_a_held_key_still_down_stays_held(self, monkeypatch: pytest.MonkeyPatch) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))
        monkeypatch.setattr(dpg, "is_key_down", lambda key: key == PIANO_KEY)

        router.sweep()

        assert holder.releases == []
        router.release(PIANO_KEY)
        assert holder.releases == [PIANO_KEY]

    def test_a_key_swept_up_takes_a_new_press_afresh(self, monkeypatch: pytest.MonkeyPatch) -> None:
        router = KeyRouter()
        holder = _Holder(claims=True)
        holder.register(router, priority=PRIORITY_PANEL)
        router.route(_key(PIANO_KEY))
        monkeypatch.setattr(dpg, "is_key_down", lambda key: False)

        router.sweep()
        router.route(_key(PIANO_KEY))

        assert holder.presses == [PIANO_KEY, PIANO_KEY]
