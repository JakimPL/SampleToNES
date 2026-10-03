from dataclasses import dataclass
from typing import Callable, List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.layout.general.plus_minus_buttons import (
    PlusMinusButtonsLayout,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.plus_minus_buttons import (
    HOLD_INITIAL_DELAY_FACTOR,
    GUIPlusMinusButtons,
)

LAYOUT = PlusMinusButtonsLayout(
    button_width=30,
    button_height=28,
    hold_delay=0.075,
)

FIRST_REPEAT = HOLD_INITIAL_DELAY_FACTOR * LAYOUT.hold_delay
FRAME = LAYOUT.hold_delay / 10


@dataclass
class Pointer:
    """Which of the pair's buttons the pointer stands on, as their hover reads it."""

    on_increment: bool = False
    on_decrement: bool = False


def _button(hovered: Callable[[], bool]) -> GUIButton:
    button = MagicMock(spec=GUIButton)
    button.is_item_hovered.side_effect = hovered
    return button


@pytest.fixture
def pointer() -> Pointer:
    return Pointer()


@pytest.fixture
def buttons(pointer: Pointer) -> GUIPlusMinusButtons:
    """A pair carrying only the state the tested methods touch, bypassing the DearPyGui-dependent
    constructor."""
    pair = GUIPlusMinusButtons.__new__(GUIPlusMinusButtons)
    pair.on_increment = None
    pair.on_decrement = None
    pair._layout = LAYOUT
    pair._held = None
    pair._increment_button = _button(lambda: pointer.on_increment)
    pair._decrement_button = _button(lambda: pointer.on_decrement)
    return pair


def _frame(buttons: GUIPlusMinusButtons, seconds: float) -> Optional[int]:
    """One frame of the left button down, answering the direction it repeats in, if any."""
    return buttons._advance_hold(buttons._held_button_hovered(), seconds)


class TestStep:
    def test_step_up_calls_increment(self, buttons: GUIPlusMinusButtons) -> None:
        calls: List[str] = []
        buttons.on_increment = lambda: calls.append("increment")
        buttons.on_decrement = lambda: calls.append("decrement")
        buttons._step(1)
        assert calls == ["increment"]

    def test_step_down_calls_decrement(self, buttons: GUIPlusMinusButtons) -> None:
        calls: List[str] = []
        buttons.on_increment = lambda: calls.append("increment")
        buttons.on_decrement = lambda: calls.append("decrement")
        buttons._step(-1)
        assert calls == ["decrement"]


class TestAHoldBelongsToTheButtonItWentDownOn:
    """A press on a button repeats while held over it, and a press carried in from elsewhere steps nothing."""

    def test_a_press_waits_the_longer_delay_before_its_first_repeat(
        self,
        buttons: GUIPlusMinusButtons,
        pointer: Pointer,
    ) -> None:
        pointer.on_increment = True
        buttons._on_increment_pressed()

        assert _frame(buttons, FIRST_REPEAT - FRAME) is None
        assert _frame(buttons, 2 * FRAME) == 1

    def test_each_later_repeat_follows_the_shorter_delay(
        self,
        buttons: GUIPlusMinusButtons,
        pointer: Pointer,
    ) -> None:
        pointer.on_decrement = True
        buttons._on_decrement_pressed()
        _frame(buttons, FIRST_REPEAT)

        assert _frame(buttons, LAYOUT.hold_delay - FRAME) is None
        assert _frame(buttons, 2 * FRAME) == -1

    def test_a_press_carried_onto_a_button_steps_nothing(
        self,
        buttons: GUIPlusMinusButtons,
        pointer: Pointer,
    ) -> None:
        pointer.on_increment = True

        assert [_frame(buttons, FIRST_REPEAT) for _ in range(3)] == [None, None, None]
        buttons._on_increment_pressed()
        assert _frame(buttons, FIRST_REPEAT) == 1

    def test_a_press_slid_onto_the_other_button_steps_nothing(
        self,
        buttons: GUIPlusMinusButtons,
        pointer: Pointer,
    ) -> None:
        pointer.on_increment = True
        buttons._on_increment_pressed()
        pointer.on_increment = False
        pointer.on_decrement = True

        assert _frame(buttons, FIRST_REPEAT) is None
        pointer.on_decrement = False
        pointer.on_increment = True
        assert _frame(buttons, FIRST_REPEAT) == 1

    def test_a_release_ends_the_hold(
        self,
        buttons: GUIPlusMinusButtons,
        pointer: Pointer,
    ) -> None:
        pointer.on_increment = True
        buttons._on_increment_pressed()

        buttons._on_mouse_release(0, None, None)

        assert buttons._held is None
        assert _frame(buttons, FIRST_REPEAT) is None
