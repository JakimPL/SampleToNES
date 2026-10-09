from dataclasses import dataclass
from typing import Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.constants.general import (
    HI_PITCH_FACTOR,
    PITCH_BEND_MAX,
    PITCH_BEND_MIN,
)
from sampletones_core.instructions import PulseInstruction, TriangleInstruction
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

PITCH: Final[int] = 60
VOLUME: Final[int] = 15


def _pulse(**bend: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=PITCH, volume=VOLUME, duty_cycle=0, **bend)


class TestTimerOffset(BaseTestSuite):
    """The two bend dimensions read as one offset, the coarse one counting sixteen steps."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        detune: int
        coarse_detune: int
        expected: int

    test_cases: Tuple["TestTimerOffset.TestCase", ...] = (
        TestCase(label="no bend", detune=0, coarse_detune=0, expected=0),
        TestCase(label="fine alone", detune=7, coarse_detune=0, expected=7),
        TestCase(label="coarse alone", detune=0, coarse_detune=3, expected=3 * HI_PITCH_FACTOR),
        TestCase(label="both", detune=-4, coarse_detune=-1, expected=-4 - HI_PITCH_FACTOR),
        TestCase(label="opposing", detune=-1, coarse_detune=1, expected=HI_PITCH_FACTOR - 1),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_offset_sums_both_dimensions(self, test_case: "TestTimerOffset.TestCase") -> None:
        instruction = _pulse(detune=test_case.detune, coarse_detune=test_case.coarse_detune)

        assert instruction.timer_offset == test_case.expected
        assert instruction.bent == (test_case.expected != 0)


class TestBendDefaults:
    def test_a_frame_states_no_bend_unless_it_names_one(self) -> None:
        assert _pulse().timer_offset == 0
        assert TriangleInstruction(on=True, pitch=PITCH).timer_offset == 0

    def test_a_bend_past_the_range_a_sequence_stores_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _pulse(detune=PITCH_BEND_MAX + 1)

        with pytest.raises(ValidationError):
            _pulse(coarse_detune=PITCH_BEND_MIN - 1)
