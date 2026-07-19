from typing import List
from unittest.mock import MagicMock, patch

from sampletones_application.utils.gui.dialog_navigation.navigator import (
    DialogKeyboardNavigator,
)
from sampletones_application.utils.gui.dialog_navigation.stop import FocusStop
from sampletones_application.utils.gui.keyboard import KeyEvent, KeyRouter

MODULE = "sampletones_application.utils.gui.dialog_navigation.navigator"

KEY_TAB = 1
KEY_RETURN = 2
KEY_ESCAPE = 3


def _dpg(*, exists: bool = True) -> MagicMock:
    dpg = MagicMock()
    dpg.mvKey_Tab = KEY_TAB
    dpg.mvKey_Return = KEY_RETURN
    dpg.mvKey_Escape = KEY_ESCAPE
    dpg.does_item_exist.return_value = exists
    return dpg


def _event(key: int, *, shift: bool = False) -> KeyEvent:
    return KeyEvent(key=key, ctrl=False, shift=shift, alt=False)


def _stops() -> List[FocusStop]:
    return [FocusStop.field("title"), FocusStop.button("ok", MagicMock())]


def _navigator(*, on_escape: MagicMock, router: KeyRouter) -> DialogKeyboardNavigator:
    return DialogKeyboardNavigator(
        window_tag="dialog",
        stops=_stops(),
        on_escape=on_escape,
        key_router=router,
        initial_index=0,
    )


class TestKeyDispatch:
    def test_tab_cycles_the_ring_forward(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_event(KEY_TAB))

        navigator._ring.cycle.assert_called_once_with(1)

    def test_shift_tab_cycles_the_ring_backward(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_event(KEY_TAB, shift=True))

        navigator._ring.cycle.assert_called_once_with(-1)

    def test_enter_activates_the_focused_stop(self) -> None:
        navigator = _navigator(on_escape=MagicMock(), router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_event(KEY_RETURN))

        navigator._ring.activate_focused.assert_called_once_with()

    def test_escape_runs_the_cancel_action(self) -> None:
        on_escape = MagicMock()
        navigator = _navigator(on_escape=on_escape, router=KeyRouter())
        navigator._ring = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()):
            navigator.handle_key(_event(KEY_ESCAPE))

        on_escape.assert_called_once_with()
        navigator._ring.cycle.assert_not_called()

    def test_key_on_a_closed_dialog_disposes(self) -> None:
        router = KeyRouter()
        navigator = _navigator(on_escape=MagicMock(), router=router)
        navigator._ring = MagicMock()
        router.push_modal(navigator)

        with patch(f"{MODULE}.dpg", _dpg(exists=False)):
            navigator.handle_key(_event(KEY_ESCAPE))

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
