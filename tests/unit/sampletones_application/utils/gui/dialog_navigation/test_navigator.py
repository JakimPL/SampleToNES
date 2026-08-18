from typing import List
from unittest.mock import MagicMock, patch

from sampletones_application.utils.gui.dialog_navigation.navigator import (
    DialogKeyboardNavigator,
)
from sampletones_application.utils.gui.dialog_navigation.stop import FocusStop
from sampletones_application.utils.gui.keyboard import KeyEvent, KeyRouter
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.shortcuts import shipped_scheme, shipped_source

MODULE = "sampletones_application.utils.gui.dialog_navigation.navigator"


def _dpg(*, exists: bool = True) -> MagicMock:
    dpg = MagicMock()
    dpg.does_item_exist.return_value = exists
    return dpg


def _press(shortcut_id: ShortcutId) -> KeyEvent:
    """The press the shipped scheme gives a dialog action."""
    combination = shipped_scheme().shortcut(shortcut_id).combination
    assert combination is not None
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


def _stops() -> List[FocusStop]:
    return [FocusStop.field("title"), FocusStop.button("ok", MagicMock())]


def _navigator(*, on_escape: MagicMock, router: KeyRouter) -> DialogKeyboardNavigator:
    return DialogKeyboardNavigator(
        window_tag="dialog",
        stops=_stops(),
        on_escape=on_escape,
        key_router=router,
        shortcut_source=shipped_source(),
        initial_index=0,
    )


class TestKeyDispatch:
    def test_the_next_control_action_cycles_the_ring_forward(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_press(ShortcutId.DIALOG_NEXT_CONTROL))

        navigator._ring.cycle.assert_called_once_with(1)

    def test_the_previous_control_action_cycles_the_ring_backward(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_press(ShortcutId.DIALOG_PREVIOUS_CONTROL))

        navigator._ring.cycle.assert_called_once_with(-1)

    def test_the_activate_action_activates_the_focused_stop(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_press(ShortcutId.DIALOG_ACTIVATE))

        navigator._ring.activate_focused.assert_called_once_with()

    def test_the_cancel_action_runs_the_cancel_callback(self) -> None:
        on_escape = MagicMock()
        navigator = _navigator(on_escape=on_escape, router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_press(ShortcutId.DIALOG_CANCEL))

        on_escape.assert_called_once_with()
        navigator._ring.cycle.assert_not_called()

    def test_a_press_the_dialog_leaves_unnamed_reaches_the_ring_not_at_all(self) -> None:
        """A dialog answers its own four actions, so a project shortcut passes the ring by."""
        on_escape = MagicMock()
        navigator = _navigator(on_escape=on_escape, router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_press(ShortcutId.SAVE_PROJECT))

        on_escape.assert_not_called()
        navigator._ring.cycle.assert_not_called()
        navigator._ring.activate_focused.assert_not_called()

    def test_key_on_a_closed_dialog_disposes(self) -> None:
        router = KeyRouter()
        navigator = _navigator(on_escape=MagicMock(), router=router)
        navigator._ring = MagicMock()
        router.push_modal(navigator)

        with patch(f"{MODULE}.dpg", _dpg(exists=False)):
            navigator.handle_key(_press(ShortcutId.DIALOG_CANCEL))

        assert not router.is_modal_open
        navigator._ring.activate_focused.assert_not_called()


class TestModalClaim:
    def test_install_claims_the_keyboard_and_defers_focus(self) -> None:
        router = KeyRouter()
        navigator = _navigator(on_escape=MagicMock(), router=router)

        with patch(f"{MODULE}.FrameCallbackManager") as frame:
            navigator.install()

        assert router.is_modal_open
        frame.set_frame_callback.assert_called_once_with(navigator._focus_initial)

    def test_dispose_releases_the_keyboard_once(self) -> None:
        router = KeyRouter()
        outer = MagicMock()
        router.push_modal(outer)
        navigator = _navigator(on_escape=MagicMock(), router=router)
        router.push_modal(navigator)

        navigator.dispose()
        navigator.dispose()

        assert router.is_modal_open

    def test_focus_initial_delegates_while_the_window_is_present(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg(exists=True)):
            navigator._focus_initial()

        navigator._ring.focus_initial.assert_called_once_with()

    def test_focus_initial_skips_a_closed_window(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg(exists=False)):
            navigator._focus_initial()

        navigator._ring.focus_initial.assert_not_called()
