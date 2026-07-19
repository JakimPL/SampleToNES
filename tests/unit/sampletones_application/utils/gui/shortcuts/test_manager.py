from typing import Dict
from unittest.mock import Mock

import pytest

from sampletones_application.utils.gui.keyboard import KeyEvent, KeyRouter
from sampletones_application.utils.gui.keyboard import focus as focus_module
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.keys import Modifier
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut

KEY = 65


@pytest.fixture(autouse=True)
def field_focus(monkeypatch: pytest.MonkeyPatch) -> Dict[str, bool]:
    state = {"focused": False}
    monkeypatch.setattr(focus_module, "is_field_focused", lambda: state["focused"])
    return state


def _manager() -> ShortcutManager:
    return ShortcutManager(key_router=KeyRouter())


def _event(*, ctrl: bool = False, shift: bool = False, alt: bool = False) -> KeyEvent:
    return KeyEvent(key=KEY, ctrl=ctrl, shift=shift, alt=alt)


class TestShortcutDispatch:
    def test_matching_shortcut_fires_and_is_claimed(self) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(ShortcutId.SAVE_PROJECT, Shortcut(KEY, (Modifier.CTRL,)), callback)
        manager.bind_all()

        claimed = manager._dispatch(_event(ctrl=True))

        assert claimed
        callback.assert_called_once()

    def test_modifier_mismatch_does_not_fire(self) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(ShortcutId.SAVE_PROJECT, Shortcut(KEY, (Modifier.CTRL,)), callback)
        manager.bind_all()

        claimed = manager._dispatch(_event(ctrl=False))

        assert not claimed
        callback.assert_not_called()

    def test_alias_reaches_the_same_callback(self) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(ShortcutId.REDO, Shortcut(KEY, (Modifier.CTRL,)), callback)
        manager.register_alias(ShortcutId.REDO, Shortcut(KEY, (Modifier.CTRL, Modifier.SHIFT)))
        manager.bind_all()

        assert manager._dispatch(_event(ctrl=True, shift=True))
        callback.assert_called_once()


class TestFieldFocusGate:
    def test_focused_input_suppresses_an_opaque_shortcut(self, field_focus: Dict[str, bool]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(ShortcutId.SAVE_PROJECT, Shortcut(KEY, (Modifier.CTRL,)), callback)
        manager.bind_all()
        field_focus["focused"] = True

        claimed = manager._dispatch(_event(ctrl=True))

        assert not claimed
        callback.assert_not_called()

    def test_field_transparent_shortcut_fires_while_focused(self, field_focus: Dict[str, bool]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.NEXT_TAB,
            Shortcut(KEY, (Modifier.CTRL,), field_transparent=True),
            callback,
        )
        manager.bind_all()
        field_focus["focused"] = True

        claimed = manager._dispatch(_event(ctrl=True))

        assert claimed
        callback.assert_called_once()

    def test_is_input_focused_reflects_the_router(self, field_focus: Dict[str, bool]) -> None:
        manager = _manager()

        field_focus["focused"] = True
        assert manager.is_input_focused

        field_focus["focused"] = False
        assert not manager.is_input_focused


class TestModalFacade:
    def test_a_pushed_modal_marks_the_dialog_open(self) -> None:
        manager = _manager()

        manager.push_modal()

        assert manager.is_dialog_open

    def test_popping_the_last_modal_releases_the_dialog(self) -> None:
        manager = _manager()
        manager.push_modal()

        manager.pop_modal()

        assert not manager.is_dialog_open

    def test_nested_modals_stay_open_until_the_last_pop(self) -> None:
        manager = _manager()
        manager.push_modal()
        manager.push_modal()

        manager.pop_modal()

        assert manager.is_dialog_open

    def test_pop_without_a_push_stays_closed(self) -> None:
        manager = _manager()

        manager.pop_modal()

        assert not manager.is_dialog_open
