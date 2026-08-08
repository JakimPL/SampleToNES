from typing import Dict
from unittest.mock import Mock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard import KeyEvent, KeyRouter
from sampletones_application.utils.gui.keyboard import focus as focus_module
from sampletones_application.utils.gui.keyboard.focus import FieldKind
from sampletones_application.utils.gui.keyboard.keys import KEY_PAGE_DOWN
from sampletones_application.utils.gui.keyboard.modifiers import (
    CTRL,
    CTRL_SHIFT,
    NO_MODIFIERS,
    SHIFT,
    ModifierSet,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource


@pytest.fixture(autouse=True)
def field_kind(monkeypatch: pytest.MonkeyPatch) -> Dict[str, FieldKind]:
    state = {"kind": FieldKind.NONE}
    monkeypatch.setattr(focus_module, "focused_field_kind", lambda: state["kind"])
    return state


def _manager(source: ShortcutSource, shortcut_id: ShortcutId, callback: Mock) -> ShortcutManager:
    """A manager holding one action, its combinations read from the scheme the source carries."""
    manager = ShortcutManager(key_router=KeyRouter(), shortcut_source=source)
    manager.register(shortcut_id, callback)
    manager.bind_all()
    return manager


def _event(key: int, *, modifiers: ModifierSet = NO_MODIFIERS) -> KeyEvent:
    return KeyEvent(key=key, modifiers=modifiers)


class TestShortcutDispatch:
    def test_the_combination_the_scheme_gives_an_action_fires_it(self, source: ShortcutSource) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.SAVE_PROJECT, callback)

        claimed = manager._dispatch(_event(dpg.mvKey_S, modifiers=CTRL))

        assert claimed
        callback.assert_called_once()

    def test_the_key_under_other_modifiers_does_not_fire(self, source: ShortcutSource) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.SAVE_PROJECT, callback)

        claimed = manager._dispatch(_event(dpg.mvKey_S))

        assert not claimed
        callback.assert_not_called()

    def test_an_alias_reaches_the_same_callback(self, source: ShortcutSource) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.REDO, callback)

        assert manager._dispatch(_event(dpg.mvKey_Z, modifiers=CTRL_SHIFT))
        callback.assert_called_once()

    def test_an_action_the_scheme_leaves_unassigned_answers_no_press(self, source: ShortcutSource) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.ABOUT_DIALOG, callback)

        assert not manager._dispatch(_event(dpg.mvKey_S, modifiers=CTRL))
        callback.assert_not_called()


class TestFieldFocusGate:
    def test_text_field_keeps_a_plain_space(
        self,
        source: ShortcutSource,
        field_kind: Dict[str, FieldKind],
    ) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.PLAY, callback)
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Spacebar))

        assert not claimed
        callback.assert_not_called()

    def test_text_field_yields_ctrl_space(
        self,
        source: ShortcutSource,
        field_kind: Dict[str, FieldKind],
    ) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.PLAY_FROM_FRAME, callback)
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Spacebar, modifiers=CTRL))

        assert claimed
        callback.assert_called_once()

    def test_text_field_keeps_its_editing_chord(
        self,
        source: ShortcutSource,
        field_kind: Dict[str, FieldKind],
    ) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.AUDIO_SETTINGS, callback)
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_A, modifiers=CTRL))

        assert not claimed
        callback.assert_not_called()

    def test_text_field_yields_a_shifted_chord_it_has_no_use_for(
        self,
        source: ShortcutSource,
        field_kind: Dict[str, FieldKind],
    ) -> None:
        """Ctrl+Shift+A carries a chord letter without being a text chord, so the shortcut fires."""
        callback = Mock()
        manager = _manager(source, ShortcutId.TOGGLE_ADVANCED_SETTINGS, callback)
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_A, modifiers=CTRL_SHIFT))

        assert claimed
        callback.assert_called_once()

    def test_focused_field_keeps_escape(
        self,
        source: ShortcutSource,
        field_kind: Dict[str, FieldKind],
    ) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.STOP, callback)
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Escape))

        assert not claimed
        callback.assert_not_called()

    def test_field_transparent_shortcut_fires_while_focused(
        self,
        source: ShortcutSource,
        field_kind: Dict[str, FieldKind],
    ) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.NEXT_TAB, callback)
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(KEY_PAGE_DOWN, modifiers=CTRL))

        assert claimed
        callback.assert_called_once()

    def test_text_field_keeps_a_shifted_space(
        self,
        source: ShortcutSource,
        field_kind: Dict[str, FieldKind],
    ) -> None:
        """Shift+Space types a space, so the key stays with the field the way a plain Space does."""
        callback = Mock()
        manager = _manager(source, ShortcutId.PLAY_FROM_START, callback)
        field_kind["kind"] = FieldKind.TEXT_ENTRY

        claimed = manager._dispatch(_event(dpg.mvKey_Spacebar, modifiers=SHIFT))

        assert not claimed
        callback.assert_not_called()
