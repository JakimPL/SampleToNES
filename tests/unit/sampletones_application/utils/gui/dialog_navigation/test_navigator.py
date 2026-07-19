from typing import List
from unittest.mock import MagicMock, patch

from sampletones_application.utils.gui.dialog_navigation.navigator import (
    DialogKeyboardNavigator,
)
from sampletones_application.utils.gui.dialog_navigation.stop import FocusStop
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager

MODULE = "sampletones_application.utils.gui.dialog_navigation.navigator"

KEY_TAB = 1
KEY_RETURN = 2
KEY_ESCAPE = 3
KEY_LSHIFT = 4
KEY_RSHIFT = 5


def _dpg(*, exists: bool = True, shift: bool = False) -> MagicMock:
    dpg = MagicMock()
    dpg.mvKey_Tab = KEY_TAB
    dpg.mvKey_Return = KEY_RETURN
    dpg.mvKey_Escape = KEY_ESCAPE
    dpg.mvKey_LShift = KEY_LSHIFT
    dpg.mvKey_RShift = KEY_RSHIFT
    dpg.does_item_exist.return_value = exists
    dpg.is_key_down.side_effect = lambda key: shift and key in (KEY_LSHIFT, KEY_RSHIFT)
    return dpg


def _stops() -> List[FocusStop]:
    return [FocusStop.field("title"), FocusStop.button("ok", MagicMock())]


def _navigator(*, on_escape: MagicMock, manager: ShortcutManager) -> DialogKeyboardNavigator:
    return DialogKeyboardNavigator(
        window_tag="dialog",
        stops=_stops(),
        on_escape=on_escape,
        shortcut_manager=manager,
        initial_index=0,
    )


class TestKeyDispatch:
    def test_tab_cycles_the_ring_forward(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), manager=ShortcutManager(key_router=KeyRouter()))
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator._on_key(sender="dialog", app_data=KEY_TAB)

        navigator._ring.cycle.assert_called_once_with(1)

    def test_shift_tab_cycles_the_ring_backward(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), manager=ShortcutManager(key_router=KeyRouter()))
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg(shift=True)):
            navigator._on_key(sender="dialog", app_data=KEY_TAB)

        navigator._ring.cycle.assert_called_once_with(-1)

    def test_enter_activates_the_focused_stop(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), manager=ShortcutManager(key_router=KeyRouter()))
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator._on_key(sender="dialog", app_data=KEY_RETURN)

        navigator._ring.activate_focused.assert_called_once_with()

    def test_escape_runs_the_cancel_action(self) -> None:
        on_escape = MagicMock()
        navigator = _navigator(on_escape=on_escape, manager=ShortcutManager(key_router=KeyRouter()))
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator._on_key(sender="dialog", app_data=KEY_ESCAPE)

        on_escape.assert_called_once_with()
        navigator._ring.cycle.assert_not_called()

    def test_key_on_a_closed_dialog_disposes(self) -> None:
        manager = ShortcutManager(key_router=KeyRouter())
        manager.push_modal()
        navigator = _navigator(on_escape=MagicMock(), manager=manager)
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg(exists=False)), patch(f"{MODULE}.dpg_delete_item"):
            navigator._on_key(sender="dialog", app_data=KEY_ESCAPE)

        assert not manager.is_dialog_open
        navigator._ring.activate_focused.assert_not_called()


class TestModalClaim:
    def test_install_claims_the_keyboard_and_defers_focus(self) -> None:
        manager = ShortcutManager(key_router=KeyRouter())
        navigator = _navigator(on_escape=MagicMock(), manager=manager)

        with (
            patch(f"{MODULE}.dpg", _dpg()) as dpg,
            patch(f"{MODULE}.FrameCallbackManager") as frame,
            patch(f"{MODULE}.dpg_delete_item"),
        ):
            navigator.install()

        assert manager.is_dialog_open
        dpg.add_key_press_handler.assert_called_once()
        frame.set_frame_callback.assert_called_once_with(navigator._focus_initial)

    def test_dispose_releases_the_keyboard_once(self) -> None:
        manager = ShortcutManager(key_router=KeyRouter())
        manager.push_modal()
        navigator = _navigator(on_escape=MagicMock(), manager=manager)

        with patch(f"{MODULE}.dpg_delete_item") as delete:
            navigator.dispose()
            navigator.dispose()

        assert not manager.is_dialog_open
        delete.assert_called_once_with(navigator._registry_tag)

    def test_focus_initial_delegates_while_the_window_is_present(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), manager=ShortcutManager(key_router=KeyRouter()))
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg(exists=True)):
            navigator._focus_initial()

        navigator._ring.focus_initial.assert_called_once_with()

    def test_focus_initial_skips_a_closed_window(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), manager=ShortcutManager(key_router=KeyRouter()))
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg(exists=False)):
            navigator._focus_initial()

        navigator._ring.focus_initial.assert_not_called()
