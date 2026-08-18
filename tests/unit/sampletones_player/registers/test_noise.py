from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_core.constants.general import MAX_PERIOD, MAX_VOLUME
from sampletones_core.instructions import NoiseInstruction
from sampletones_player.registers.noise import NoiseRegisters
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestNoiseRegisters(BaseTestSuite):
    """The project counts noise periods from the slowest and the register from the fastest."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[int, int]
        period: int
        short: bool

        @property
        def label(self) -> str:
            mode = "short" if self.short else "normal"
            return f"period_{self.period}_{mode}"

    test_cases = (
        TestCase(period=0, short=False, expected=(0x3F, MAX_PERIOD)),
        TestCase(period=MAX_PERIOD, short=False, expected=(0x3F, 0)),
        TestCase(period=0, short=True, expected=(0x3F, 0x80 | MAX_PERIOD)),
        TestCase(period=MAX_PERIOD, short=True, expected=(0x3F, 0x80)),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_registers_match(self, test_case: TestCase) -> None:
        instruction = NoiseInstruction(
            on=True,
            period=test_case.period,
            volume=MAX_VOLUME,
            short=test_case.short,
        )
        registers = NoiseRegisters.from_instructions([instruction])
        assert registers[0].values == test_case.expected

    def test_rest_clears_the_volume_and_keeps_the_period(self) -> None:
        instructions = [
            NoiseInstruction(on=True, period=4, volume=MAX_VOLUME, short=False),
            NoiseInstruction.null_instruction(),
        ]
        sounding, resting = NoiseRegisters.from_instructions(instructions)[:2]
        assert resting.control & 0x0F == 0
        assert resting.period == sounding.period
