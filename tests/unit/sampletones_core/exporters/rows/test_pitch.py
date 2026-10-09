from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_core.constants.general import MAX_PITCH, MIN_PLAYED_PITCH
from sampletones_core.exporters.rows.pitch import FLAT_CONTOUR_STEP, highest_step, written_pitch
from sampletones_core.utils.frequencies import transpose_pitch
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

CONTOUR: Final[Tuple[int, ...]] = (-5, 0, 5)
CONTOUR_TOP: Final[int] = max(CONTOUR)
FLAT_CONTOUR: Final[Tuple[int, ...]] = (FLAT_CONTOUR_STEP,)
MIDDLE_PITCH: Final[int] = 60


class TestTheHighestStep:
    def test_the_highest_step_of_a_contour(self) -> None:
        assert highest_step(CONTOUR) == CONTOUR_TOP

    def test_a_contour_of_no_steps_moves_nothing(self) -> None:
        assert highest_step(()) == FLAT_CONTOUR_STEP


class TestTheWrittenPitch(BaseTestSuite):
    """The song holds each tick's transposed pitch within the range the channels play, and a tracker
    moves the written note by the contour's step each tick. The written pitch is the one that keeps
    each tick the song plays within that range on its own note.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        pitch: int
        contour: Tuple[int, ...]
        expected: int

    test_cases: Tuple["TestTheWrittenPitch.TestCase", ...] = (
        TestCase(
            label="within the range",
            pitch=MIDDLE_PITCH,
            contour=CONTOUR,
            expected=MIDDLE_PITCH,
        ),
        TestCase(
            label="a flat contour below the range",
            pitch=MIN_PLAYED_PITCH - 3,
            contour=FLAT_CONTOUR,
            expected=MIN_PLAYED_PITCH,
        ),
        TestCase(
            label="a contour reaching into the range",
            pitch=MIN_PLAYED_PITCH - 2,
            contour=CONTOUR,
            expected=MIN_PLAYED_PITCH - 2,
        ),
        TestCase(
            label="a contour lying below the range",
            pitch=MIN_PLAYED_PITCH - 10,
            contour=CONTOUR,
            expected=MIN_PLAYED_PITCH - CONTOUR_TOP,
        ),
        TestCase(
            label="a flat contour above the range",
            pitch=MAX_PITCH + 4,
            contour=FLAT_CONTOUR,
            expected=MAX_PITCH,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_pitch_written(self, test_case: "TestTheWrittenPitch.TestCase") -> None:
        assert written_pitch(test_case.pitch, highest_step(test_case.contour)) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_tick_the_song_plays_within_the_range_keeps_its_note(
        self,
        test_case: "TestTheWrittenPitch.TestCase",
    ) -> None:
        """A tick the song holds at C-0 the tracker holds there too, and the highest tick of a contour
        lying below the range lands on C-0 itself.
        """
        contour_top = highest_step(test_case.contour)
        written = written_pitch(test_case.pitch, contour_top)

        for step in test_case.contour:
            song_pitch = transpose_pitch(test_case.pitch, step)
            tracker_pitch = min(MAX_PITCH, written + step)
            if song_pitch > MIN_PLAYED_PITCH or step == contour_top:
                assert tracker_pitch == song_pitch
            else:
                assert tracker_pitch <= MIN_PLAYED_PITCH
