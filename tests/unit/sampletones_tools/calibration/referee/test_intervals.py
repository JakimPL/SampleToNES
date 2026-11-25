from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_shared.constants.music import A4_FREQUENCY, OCTAVE_SEMITONES
from sampletones_tools.calibration.referee.intervals import (
    CENTS_PER_SEMITONE,
    cents_between,
    line_semitones,
    nearest_semitone,
    octaves_between,
    same_pitch_class,
    semitones_between,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SEMITONE_RATIO: Final[float] = 2.0 ** (1.0 / OCTAVE_SEMITONES)
QUARTER_TONE_RATIO: Final[float] = 2.0 ** (0.4 / OCTAVE_SEMITONES)


class TestIntervals:
    def test_an_octave_up_is_one_octave_twelve_semitones_and_twelve_hundred_cents(self) -> None:
        assert octaves_between(2 * A4_FREQUENCY, A4_FREQUENCY) == 1.0
        assert semitones_between(2 * A4_FREQUENCY, A4_FREQUENCY) == OCTAVE_SEMITONES
        assert cents_between(2 * A4_FREQUENCY, A4_FREQUENCY) == OCTAVE_SEMITONES * CENTS_PER_SEMITONE

    def test_a_lower_frequency_stands_below_zero(self) -> None:
        assert semitones_between(A4_FREQUENCY / SEMITONE_RATIO, A4_FREQUENCY) == pytest.approx(-1.0)

    def test_the_nearest_semitone_counts_from_a4(self) -> None:
        assert nearest_semitone(A4_FREQUENCY) == 0
        assert nearest_semitone(A4_FREQUENCY * SEMITONE_RATIO * QUARTER_TONE_RATIO) == 1

    def test_a_line_keeps_its_silent_frames(self) -> None:
        assert line_semitones((A4_FREQUENCY, None, 2 * A4_FREQUENCY)) == [0, None, OCTAVE_SEMITONES]

    def test_an_empty_line_holds_no_semitone(self) -> None:
        assert not line_semitones(())


class TestSamePitchClass(BaseTestSuite):
    """A frequency names a target's note where its nearest semitone lies whole octaves off, either way."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        ratio: float
        expected: bool

    test_cases = (
        TestCase(label="unison", ratio=1.0, expected=True),
        TestCase(label="octave_up", ratio=2.0, expected=True),
        TestCase(label="two_octaves_down", ratio=0.25, expected=True),
        TestCase(label="octave_within_half_a_semitone", ratio=2.0 * QUARTER_TONE_RATIO, expected=True),
        TestCase(label="semitone_up", ratio=SEMITONE_RATIO, expected=False),
        TestCase(label="semitone_under_an_octave", ratio=2.0 / SEMITONE_RATIO, expected=False),
        TestCase(label="fifth", ratio=SEMITONE_RATIO**7, expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_frequency_names_the_target_s_note_in_whole_octaves(self, test_case: TestCase) -> None:
        assert same_pitch_class(A4_FREQUENCY * test_case.ratio, A4_FREQUENCY) is test_case.expected
