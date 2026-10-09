from dataclasses import dataclass
from typing import List, Tuple

import pytest

from sampletones_core.instructions import InstructionUnion, PulseInstruction, sounds
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


def _pulse() -> PulseInstruction:
    return PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)


def _rest() -> PulseInstruction:
    return PulseInstruction.null_instruction()


class TestSounds(BaseTestSuite):
    """A stream sounds where any of its frames does, which is what puts a channel in play."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        stream: List[InstructionUnion]

    test_cases: Tuple["TestSounds.TestCase", ...] = (
        TestCase(label="sounding in one frame", stream=[_rest(), _pulse(), _rest()], expected=True),
        TestCase(label="sounding throughout", stream=[_pulse(), _pulse()], expected=True),
        TestCase(label="resting throughout", stream=[_rest(), _rest()], expected=False),
        TestCase(label="no frames", stream=[], expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_stream_sounds_where_a_frame_does(self, test_case: TestCase) -> None:
        assert sounds(test_case.stream) is test_case.expected
