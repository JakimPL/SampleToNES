from dataclasses import dataclass
from typing import Final, List, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.intervals import CENTS_PER_SEMITONE
from sampletones_tools.calibration.referee.pitch import (
    CENTS,
    EXACT,
    OCTAVE,
    SEMITONE,
    SILENT,
    WRONG,
    PitchReferee,
    PitchTally,
    answer_of,
)
from sampletones_tools.calibration.referee.protocol import Judgment
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 4
BASS_NOTE: Final[int] = 45
BASS: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=BASS_NOTE)] * FRAMES
OCTAVE_CENTS: Final[float] = 1200.0
HALF_SEMITONE_CENTS: Final[float] = CENTS_PER_SEMITONE / 2
TARGET: Final[float] = 220.0


def _triangle(pitch: int) -> List[InstructionUnion]:
    return [TriangleInstruction(on=True, pitch=pitch)] * FRAMES


def _judged(truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(PitchReferee().judge(truth, reconstruction))


class TestAnswerOf(BaseTestSuite):
    """Each sounding channel's offset reads as its nearest semitone step, and the best answer counts."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        offsets: Tuple[float, ...]
        expected: str

    test_cases = (
        TestCase(label="no_channel_sounding", offsets=(), expected=SILENT),
        TestCase(label="just_under_half_a_semitone_up", offsets=(HALF_SEMITONE_CENTS - 1,), expected=EXACT),
        TestCase(label="just_under_half_a_semitone_down", offsets=(1 - HALF_SEMITONE_CENTS,), expected=EXACT),
        TestCase(label="an_octave_up", offsets=(OCTAVE_CENTS,), expected=OCTAVE),
        TestCase(label="two_octaves_down", offsets=(-2 * OCTAVE_CENTS,), expected=OCTAVE),
        TestCase(label="a_semitone_up", offsets=(CENTS_PER_SEMITONE,), expected=SEMITONE),
        TestCase(label="a_semitone_down", offsets=(-CENTS_PER_SEMITONE,), expected=SEMITONE),
        TestCase(label="a_semitone_under_an_octave", offsets=(OCTAVE_CENTS - CENTS_PER_SEMITONE,), expected=WRONG),
        TestCase(label="a_fifth", offsets=(7 * CENTS_PER_SEMITONE,), expected=WRONG),
        TestCase(label="on_pitch_beside_a_wrong_note", offsets=(700.0, 10.0), expected=EXACT),
        TestCase(
            label="an_octave_outranks_a_nearer_semitone",
            offsets=(CENTS_PER_SEMITONE, OCTAVE_CENTS),
            expected=OCTAVE,
        ),
        TestCase(label="a_semitone_outranks_a_wrong_note", offsets=(700.0, -CENTS_PER_SEMITONE), expected=SEMITONE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_best_answer_any_channel_gives_counts(self, test_case: TestCase) -> None:
        assert answer_of(test_case.offsets) == test_case.expected


class TestPitchTally:
    def test_the_cents_reading_holds_the_nearest_answer_on_pitch(self) -> None:
        tally = PitchTally()
        tally.add(TARGET, [TARGET * 2.0 ** (30 / OCTAVE_CENTS), TARGET * 2.0 ** (-10 / OCTAVE_CENTS)])
        tally.add(TARGET, [TARGET * 2.0 ** (20 / OCTAVE_CENTS)])

        judgment = judged(tally.judgment())

        assert judgment.components[CENTS] == pytest.approx(15.0)
        assert judgment.score == 0.0

    def test_no_frame_answered_on_pitch_holds_no_cents_reading(self) -> None:
        tally = PitchTally()
        tally.add(TARGET, [])

        assert CENTS not in judged(tally.judgment()).components

    def test_no_frame_counted_is_left_unjudged(self) -> None:
        assert PitchTally().judgment() is None


class TestPitchReferee:
    def test_a_conversion_on_pitch_scores_zero(self) -> None:
        judgment = _judged(written_truth({ChannelName.TRIANGLE: BASS}), converted({ChannelName.TRIANGLE: BASS}))

        assert judgment.score == 0.0
        assert judgment.components[CENTS] == pytest.approx(0.0)

    @pytest.mark.parametrize(
        ("played", "answer"),
        [(BASS_NOTE + 12, OCTAVE), (BASS_NOTE - 1, SEMITONE), (BASS_NOTE + 7, WRONG)],
        ids=["octave", "semitone", "fifth"],
    )
    def test_a_note_off_the_line_counts_by_how_far_it_stands(self, played: int, answer: str) -> None:
        judgment = _judged(
            written_truth({ChannelName.TRIANGLE: BASS}), converted({ChannelName.TRIANGLE: _triangle(played)})
        )

        assert judgment.score == 1.0
        assert judgment.components[answer] == 1.0

    def test_a_line_no_tonal_channel_answers_is_silent(self) -> None:
        silent = [TriangleInstruction(on=False, pitch=BASS_NOTE)] * FRAMES

        judgment = _judged(written_truth({ChannelName.TRIANGLE: BASS}), converted({ChannelName.TRIANGLE: silent}))

        assert judgment.components[SILENT] == 1.0

    def test_a_line_is_answered_by_whichever_channel_carries_it(self) -> None:
        line = written_truth(
            {ChannelName.PULSE1: [PulseInstruction(on=True, pitch=57, volume=9, duty_cycle=2)] * FRAMES}
        )

        assert _judged(line, converted({ChannelName.TRIANGLE: _triangle(69)})).score == 0.0

    def test_a_line_is_read_over_the_frames_the_conversion_plays(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES + (220.0,) * FRAMES})

        assert _judged(truth, converted({ChannelName.TRIANGLE: _triangle(57)})).score == 0.0

    def test_a_synthesized_line_is_read_from_its_frequencies(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES})

        assert _judged(truth, converted({ChannelName.TRIANGLE: _triangle(57)})).score == 0.0

    def test_a_sound_of_no_line_is_left_unjudged(self) -> None:
        hiss = [NoiseInstruction(on=True, period=6, volume=10, short=False)] * FRAMES

        assert (
            PitchReferee().judge(written_truth({ChannelName.NOISE: hiss}), converted({ChannelName.NOISE: hiss})) is None
        )

    def test_an_empty_line_beside_a_sounding_conversion_is_left_unjudged(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": ()})

        assert PitchReferee().judge(truth, converted({ChannelName.TRIANGLE: BASS})) is None
