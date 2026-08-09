from typing import Dict, Iterator
from unittest.mock import Mock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard import KeyEvent, KeyRouter
from sampletones_application.utils.gui.keyboard import focus as focus_module
from sampletones_application.utils.gui.keyboard.focus import FieldKind
from sampletones_application.utils.gui.keyboard.keys import KEY_PAGE_DOWN
from sampletones_application.utils.gui.keyboard.modifiers import (
    CTRL,
    CTRL_ALT,
    CTRL_SHIFT,
    NO_MODIFIERS,
    SHIFT,
    ModifierSet,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.gui.shortcuts.written import WrittenShortcut
from tests.unit.sampletones_application.utils.gui.shortcuts.conftest import RebindScheme


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


def _menu_manager(source: ShortcutSource) -> ShortcutManager:
    """A manager holding one action, its menu item created the way the menu bar creates it."""
    manager = ShortcutManager(key_router=KeyRouter(), shortcut_source=source)
    manager.register(ShortcutId.SAVE_PROJECT, Mock())
    with dpg.window(), dpg.menu_bar(), dpg.menu(label="File"):
        manager.add_menu_item(ShortcutId.SAVE_PROJECT, label="Save")

    return manager


def _event(key: int, *, modifiers: ModifierSet = NO_MODIFIERS) -> KeyEvent:
    return KeyEvent(key=key, modifiers=modifiers)


@pytest.fixture(name="dpg_context")
def dpg_context_fixture() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


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


class TestRebind:
    """A registration names the action, so activating another scheme changes the keys that fire it."""

    def test_the_combination_the_new_scheme_gives_an_action_fires_it(
        self,
        source: ShortcutSource,
        rebound: RebindScheme,
    ) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.SAVE_PROJECT, callback)

        source.activate(rebound({ShortcutId.SAVE_PROJECT: WrittenShortcut(combination="Ctrl+Alt+K")}))
        manager.rebind()

        assert manager._dispatch(_event(dpg.mvKey_K, modifiers=CTRL_ALT))
        callback.assert_called_once()

    def test_the_combination_the_new_scheme_took_away_stops_firing_it(
        self,
        source: ShortcutSource,
        rebound: RebindScheme,
    ) -> None:
        callback = Mock()
        manager = _manager(source, ShortcutId.SAVE_PROJECT, callback)

        source.activate(rebound({ShortcutId.SAVE_PROJECT: WrittenShortcut(combination="Ctrl+Alt+K")}))
        manager.rebind()

        assert not manager._dispatch(_event(dpg.mvKey_S, modifiers=CTRL))
        callback.assert_not_called()

    def test_a_rebind_leaves_the_router_the_one_scope_it_was_given(
        self,
        source: ShortcutSource,
        rebound: RebindScheme,
    ) -> None:
        """The scope is claimed at bind time, so repeated rebinds keep one handler on the router."""
        router = KeyRouter()
        manager = ShortcutManager(key_router=router, shortcut_source=source)
        manager.register(ShortcutId.SAVE_PROJECT, Mock())
        manager.bind_all()
        scopes = len(router._scopes)

        source.activate(rebound({ShortcutId.SAVE_PROJECT: WrittenShortcut(combination="Ctrl+Alt+K")}))
        manager.rebind()

        assert len(router._scopes) == scopes


class TestMenuAccelerators:
    """A menu item prints the keys that also fire it, which a rebind keeps true."""

    def test_a_menu_item_prints_the_combination_the_scheme_gives_its_action(
        self,
        dpg_context: None,
        source: ShortcutSource,
    ) -> None:
        manager = _menu_manager(source)
        item = next(iter(manager._menu_items))

        assert dpg.get_item_configuration(item)["shortcut"] == "Ctrl+S"

    def test_a_rebind_prints_the_keys_now_in_place(
        self,
        dpg_context: None,
        source: ShortcutSource,
        rebound: RebindScheme,
    ) -> None:
        manager = _menu_manager(source)
        item = next(iter(manager._menu_items))

        source.activate(rebound({ShortcutId.SAVE_PROJECT: WrittenShortcut(combination="Ctrl+Alt+K")}))
        manager.rebind()

        assert dpg.get_item_configuration(item)["shortcut"] == "Ctrl+Alt+K"


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
