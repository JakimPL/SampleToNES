from typing import Dict
from unittest.mock import Mock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard import KeyEvent, KeyRouter
from sampletones_application.utils.gui.keyboard import focus as focus_module
from sampletones_application.utils.gui.keyboard.focus import FieldKind
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.keys import Modifier
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


def _event(key: int = KEY, *, ctrl: bool = False, shift: bool = False, alt: bool = False) -> KeyEvent:
    return KeyEvent(key=key, ctrl=ctrl, shift=shift, alt=alt)


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
    def test_text_field_keeps_a_plain_space(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(ShortcutId.PLAY, Shortcut(dpg.mvKey_Spacebar), callback)
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Spacebar))

        assert not claimed
        callback.assert_not_called()

    def test_text_field_yields_ctrl_space(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(ShortcutId.PLAY_FROM_FRAME, Shortcut(dpg.mvKey_Spacebar, (Modifier.CTRL,)), callback)
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Spacebar, ctrl=True))

        assert claimed
        callback.assert_called_once()

    def test_text_field_keeps_its_editing_chord(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(ShortcutId.AUDIO_SETTINGS, Shortcut(dpg.mvKey_A, (Modifier.CTRL,)), callback)
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_A, ctrl=True))

        assert not claimed
        callback.assert_not_called()

    def test_focused_field_keeps_escape(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()
        callback = Mock()
        manager.register(ShortcutId.STOP, Shortcut(dpg.mvKey_Escape), callback)
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
            Shortcut(KEY, (Modifier.CTRL,), field_transparent=True),
            callback,
        )
        manager.bind_all()
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(ctrl=True))

        assert claimed
        callback.assert_called_once()

    def test_is_input_focused_reflects_the_router(self, field_kind: Dict[str, FieldKind]) -> None:
        manager = _manager()

        field_kind["kind"] = FieldKind.TEXT_ENTRY
        assert manager.is_input_focused

        field_kind["kind"] = FieldKind.NONE
        assert not manager.is_input_focused
