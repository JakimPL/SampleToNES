from typing import Dict
from unittest.mock import Mock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard import (
    KeyCombination,
    KeyEvent,
    KeyRouter,
)
from sampletones_application.utils.gui.keyboard import focus as focus_module
from sampletones_application.utils.gui.keyboard.focus import FieldKind
from sampletones_application.utils.gui.keyboard.modifiers import (
    CTRL,
    CTRL_SHIFT,
    NO_MODIFIERS,
    ModifierSet,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut

KEY = 65


@pytest.fixture(autouse=True)
def field_kind(monkeypatch: pytest.MonkeyPatch) -> Dict[str, FieldKind]:
    state = {"kind": FieldKind.NONE}
    monkeypatch.setattr(focus_module, "focused_field_kind", lambda: state["kind"])
    return state


def _manager() -> ShortcutManager:
    return ShortcutManager(key_router=KeyRouter())


def _event(key: int = KEY, *, modifiers: ModifierSet = NO_MODIFIERS) -> KeyEvent:
    return KeyEvent(key=key, modifiers=modifiers)


class TestShortcutDispatch:
    def test_matching_shortcut_fires_and_is_claimed(self) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.SAVE_PROJECT,
            Shortcut(combination=KeyCombination(KEY, CTRL)),
            callback,
        )
        manager.bind_all()

        claimed = manager._dispatch(_event(modifiers=CTRL))

        assert claimed
        callback.assert_called_once()

    def test_modifier_mismatch_does_not_fire(self) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.SAVE_PROJECT,
            Shortcut(combination=KeyCombination(KEY, CTRL)),
            callback,
        )
        manager.bind_all()

        claimed = manager._dispatch(_event())

        assert not claimed
        callback.assert_not_called()

    def test_alias_reaches_the_same_callback(self) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.REDO,
            Shortcut(
                combination=KeyCombination(KEY, CTRL),
                aliases=(KeyCombination(KEY, CTRL_SHIFT),),
            ),
            callback,
        )
        manager.bind_all()

        assert manager._dispatch(_event(modifiers=CTRL_SHIFT))
        callback.assert_called_once()


class TestFieldFocusGate:
    def test_text_field_keeps_a_plain_space(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.PLAY,
            Shortcut(combination=KeyCombination(dpg.mvKey_Spacebar)),
            callback,
        )
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Spacebar))

        assert not claimed
        callback.assert_not_called()

    def test_text_field_yields_ctrl_space(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.PLAY_FROM_FRAME,
            Shortcut(combination=KeyCombination(dpg.mvKey_Spacebar, CTRL)),
            callback,
        )
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Spacebar, modifiers=CTRL))

        assert claimed
        callback.assert_called_once()

    def test_text_field_keeps_its_editing_chord(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.AUDIO_SETTINGS,
            Shortcut(combination=KeyCombination(dpg.mvKey_A, CTRL)),
            callback,
        )
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_A, modifiers=CTRL))

        assert not claimed
        callback.assert_not_called()

    def test_text_field_yields_a_shifted_chord_it_has_no_use_for(self, field_kind: Dict[str, FieldKind]) -> None:
        """Ctrl+Shift+A carries a chord letter without being a text chord, so the shortcut fires."""
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.TOGGLE_ADVANCED_SETTINGS,
            Shortcut(combination=KeyCombination(dpg.mvKey_A, CTRL_SHIFT)),
            callback,
        )
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_A, modifiers=CTRL_SHIFT))

        assert claimed
        callback.assert_called_once()

    def test_focused_field_keeps_escape(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.STOP,
            Shortcut(combination=KeyCombination(dpg.mvKey_Escape)),
            callback,
        )
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Escape))

        assert not claimed
        callback.assert_not_called()

    def test_field_transparent_shortcut_fires_while_focused(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(
            ShortcutId.NEXT_TAB,
            Shortcut(
                combination=KeyCombination(KEY, CTRL),
                field_transparent=True,
            ),
            callback,
        )
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(modifiers=CTRL))

        assert claimed
        callback.assert_called_once()
