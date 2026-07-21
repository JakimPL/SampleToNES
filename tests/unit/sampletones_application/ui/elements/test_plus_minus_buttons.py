from typing import List

from sampletones_application.layout.general.plus_minus_buttons import PlusMinusButtonsLayout
from sampletones_application.ui.elements.plus_minus_buttons import GUIPlusMinusButtons

LAYOUT = PlusMinusButtonsLayout(
    button_width=30,
    button_height=28,
    hold_delay=0.075,
)


def _buttons() -> GUIPlusMinusButtons:
    """A pair carrying only the state the tested methods touch, bypassing the DearPyGui-dependent
    constructor."""
    buttons = GUIPlusMinusButtons.__new__(GUIPlusMinusButtons)
    buttons.on_increment = None
    buttons.on_decrement = None
    buttons._layout = LAYOUT
    buttons._hold_direction = None
    buttons._hold_timer = None
    return buttons


class TestStep:
    def test_step_up_calls_increment(self) -> None:
        buttons = _buttons()
        calls: List[str] = []
        buttons.on_increment = lambda: calls.append("increment")
        buttons.on_decrement = lambda: calls.append("decrement")
        buttons._step(1)
        assert calls == ["increment"]

    def test_step_down_calls_decrement(self) -> None:
        buttons = _buttons()
        calls: List[str] = []
        buttons.on_increment = lambda: calls.append("increment")
        buttons.on_decrement = lambda: calls.append("decrement")
        buttons._step(-1)
        assert calls == ["decrement"]


class TestHoldTimer:
    def test_first_press_arms_timer_without_stepping(self) -> None:
        buttons = _buttons()
        assert buttons._update_hold_timer(False, True, 0.0) is None
        assert buttons._hold_timer is not None

    def test_repeats_once_the_delay_elapses(self) -> None:
        buttons = _buttons()
        buttons._update_hold_timer(False, True, 0.0)
        buttons._hold_timer = 0.0
        assert buttons._update_hold_timer(False, True, 0.01) == 1

    def test_no_button_pressed_returns_none(self) -> None:
        buttons = _buttons()
        assert buttons._update_hold_timer(False, False, 0.05) is None

    def test_release_clears_hold_state(self) -> None:
        buttons = _buttons()
        buttons._update_hold_timer(True, False, 0.0)
        buttons._on_mouse_release(0, None, None)
        assert buttons._hold_timer is None
        assert buttons._hold_direction is None
