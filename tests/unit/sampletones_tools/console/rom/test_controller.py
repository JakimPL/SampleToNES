from dataclasses import dataclass
from typing import Final, List, Tuple

import pytest

from sampletones_tools.console.rom.controller import NO_BUTTONS, Button, Controller
from sampletones_tools.console.rom.registers import CONTROLLER_DATA_MASK, OPEN_BUS
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

STROBE_HIGH: Final[int] = 0x01
STROBE_LOW: Final[int] = 0x00
BUTTON_COUNT: Final[int] = 8
READS_PAST_THE_BUTTONS: Final[int] = 4


def _latched(buttons: Button) -> Controller:
    controller = Controller()
    controller.hold(buttons)
    controller.write(STROBE_HIGH)
    controller.write(STROBE_LOW)
    return controller


def _pressed(controller: Controller, reads: int) -> List[int]:
    return [controller.read() & CONTROLLER_DATA_MASK for _ in range(reads)]


class TestTheSerialOrder(BaseTestSuite):
    """A latched controller answers one button a read, in the order the hardware shifts them out."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        button: Button
        expected: int

        @property
        def label(self) -> str:
            return str(self.button.name)

    test_cases: Tuple[TestCase, ...] = (
        TestCase(button=Button.A, expected=0),
        TestCase(button=Button.B, expected=1),
        TestCase(button=Button.SELECT, expected=2),
        TestCase(button=Button.START, expected=3),
        TestCase(button=Button.UP, expected=4),
        TestCase(button=Button.DOWN, expected=5),
        TestCase(button=Button.LEFT, expected=6),
        TestCase(button=Button.RIGHT, expected=7),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_button_answers_on_its_own_read(self, test_case: TestCase) -> None:
        pressed = _pressed(_latched(test_case.button), BUTTON_COUNT)

        assert [read for read, bit in enumerate(pressed) if bit] == [test_case.expected]


class TestReading:
    def test_several_buttons_answer_each_on_its_read(self) -> None:
        assert _pressed(_latched(Button.A | Button.START | Button.RIGHT), BUTTON_COUNT) == [1, 0, 0, 1, 0, 0, 0, 1]

    def test_a_read_past_the_eighth_answers_with_a_set_bit(self) -> None:
        controller = _latched(NO_BUTTONS)
        _pressed(controller, BUTTON_COUNT)

        assert _pressed(controller, READS_PAST_THE_BUTTONS) == [1] * READS_PAST_THE_BUTTONS

    def test_every_read_carries_the_bit_the_open_bus_leaves_set(self) -> None:
        controller = _latched(Button.B)

        assert all(controller.read() & OPEN_BUS for _ in range(BUTTON_COUNT))

    def test_a_high_strobe_keeps_answering_with_the_first_button(self) -> None:
        controller = Controller()
        controller.hold(Button.A)
        controller.write(STROBE_HIGH)

        assert _pressed(controller, BUTTON_COUNT) == [1] * BUTTON_COUNT

    def test_the_buttons_are_latched_as_the_strobe_falls(self) -> None:
        controller = _latched(Button.B)
        controller.hold(Button.A)

        assert _pressed(controller, BUTTON_COUNT) == [0, 1, 0, 0, 0, 0, 0, 0]
