from dataclasses import dataclass
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import (
    InstructionUnion,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.continuity import (
    FRAGMENTS,
    HANDOVERS,
    Answer,
    ContinuityReferee,
    NoteAnswers,
    answer_at,
    note_spans,
)
from sampletones_tools.calibration.referee.protocol import Judgment
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 8
BASS: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=57)] * FRAMES
SILENT_TRIANGLE: Final[InstructionUnion] = TriangleInstruction.null_instruction()
PULSE_BASS: Final[InstructionUnion] = PulseInstruction(on=True, pitch=45, volume=10, duty_cycle=2)
SILENT_PULSE: Final[InstructionUnion] = PulseInstruction.null_instruction()
LOWER: Final[InstructionUnion] = PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=2)
UPPER: Final[InstructionUnion] = PulseInstruction(on=True, pitch=64, volume=10, duty_cycle=2)
INTERVAL: Final[Dict[ChannelName, List[InstructionUnion]]] = {
    ChannelName.PULSE1: [LOWER] * FRAMES,
    ChannelName.PULSE2: [UPPER] * FRAMES,
}
TRIANGLE: Final[ChannelName] = ChannelName.TRIANGLE
PULSE: Final[ChannelName] = ChannelName.PULSE1
LOW_NOTE: Final[float] = 110.0
HIGH_NOTE: Final[float] = 220.0


def _judged(truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(ContinuityReferee().judge(truth, reconstruction))


class TestNoteAnswers(BaseTestSuite):
    """A note counts each change of its answering channel and each separate run answering it."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        answers: Tuple[Answer, ...]
        expected: Tuple[int, int]

    test_cases = (
        TestCase(label="one_channel_throughout", answers=(TRIANGLE, TRIANGLE, TRIANGLE), expected=(0, 1)),
        TestCase(label="a_channel_taking_over", answers=(TRIANGLE, PULSE, PULSE), expected=(1, 1)),
        TestCase(label="a_dropout_on_one_channel", answers=(TRIANGLE, None, TRIANGLE), expected=(0, 2)),
        TestCase(label="a_dropout_between_two_channels", answers=(TRIANGLE, None, PULSE), expected=(1, 2)),
        TestCase(label="a_late_entry", answers=(None, None, TRIANGLE), expected=(0, 1)),
        TestCase(label="a_silent_note", answers=(None, None), expected=(0, 0)),
        TestCase(label="a_note_of_no_frame", answers=(), expected=(0, 0)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_note_counts_its_handovers_and_fragments(self, test_case: TestCase) -> None:
        note = NoteAnswers(answers=test_case.answers)

        assert (note.handovers, note.fragments) == test_case.expected


class TestAnswerAt:
    def test_the_channel_nearest_the_note_answers_it(self) -> None:
        played = {PULSE: (2 * LOW_NOTE,), TRIANGLE: (LOW_NOTE * 1.06,)}

        assert answer_at(played, 0, LOW_NOTE) == TRIANGLE

    def test_two_channels_as_near_answer_as_the_one_named_first(self) -> None:
        played = {ChannelName.PULSE2: (LOW_NOTE,), ChannelName.PULSE1: (LOW_NOTE,)}

        assert answer_at(played, 0, LOW_NOTE) == ChannelName.PULSE1

    def test_a_channel_however_far_answers_where_it_sounds_alone(self) -> None:
        assert answer_at({PULSE: (8 * LOW_NOTE,)}, 0, LOW_NOTE) == PULSE

    def test_no_sounding_channel_leaves_the_frame_unanswered(self) -> None:
        assert answer_at({PULSE: (None,)}, 0, LOW_NOTE) is None


class TestNoteSpans:
    def test_a_line_splits_into_notes_where_it_changes_pitch_or_falls_silent(self) -> None:
        spans = note_spans((110.0, 110.0, 220.0, None, 220.0))

        assert [(span.start, span.end) for span in spans] == [(0, 2), (2, 3), (4, 5)]

    def test_a_note_is_answered_against_its_first_frame(self) -> None:
        wavering = LOW_NOTE * 2.0 ** (0.3 / 12.0)

        spans = note_spans((LOW_NOTE, wavering, LOW_NOTE))

        assert [(span.start, span.end, span.target) for span in spans] == [(0, 3, LOW_NOTE)]

    def test_a_silent_or_empty_line_holds_no_note(self) -> None:
        assert not note_spans((None, None))
        assert not note_spans(())


class TestContinuityReferee:
    def test_a_note_held_on_one_channel_scores_zero(self) -> None:
        judgment = _judged(written_truth({ChannelName.TRIANGLE: BASS}), converted({ChannelName.TRIANGLE: BASS}))

        assert judgment.score == 0.0
        assert (judgment.components[HANDOVERS], judgment.components[FRAGMENTS]) == (0.0, 1.0)

    def test_a_note_handed_from_the_triangle_to_a_pulse_counts_one_handover(self) -> None:
        half = FRAMES // 2
        played = {
            ChannelName.TRIANGLE: BASS[:half] + [SILENT_TRIANGLE] * half,
            ChannelName.PULSE1: [SILENT_PULSE] * half + [PULSE_BASS] * half,
        }

        judgment = _judged(written_truth({ChannelName.TRIANGLE: BASS}), converted(played))

        assert judgment.components[HANDOVERS] == 1.0
        assert judgment.score == 1.0

    def test_a_dropout_inside_a_note_counts_a_second_fragment(self) -> None:
        played = {ChannelName.TRIANGLE: BASS[:3] + [SILENT_TRIANGLE] * 2 + BASS[5:]}

        judgment = _judged(written_truth({ChannelName.TRIANGLE: BASS}), converted(played))

        assert judgment.components[FRAGMENTS] == 2.0
        assert judgment.score == 1.0

    def test_two_pulses_holding_each_other_s_lines_throughout_score_zero(self) -> None:
        played = {ChannelName.PULSE1: [UPPER] * FRAMES, ChannelName.PULSE2: [LOWER] * FRAMES}

        judgment = _judged(written_truth(INTERVAL), converted(played))

        assert judgment.score == 0.0

    def test_two_pulses_trading_their_lines_count_a_handover_at_each_trade(self) -> None:
        """Pulses playing C E E C and E C C E hand each note over twice."""
        quarter = FRAMES // 4
        played = {
            ChannelName.PULSE1: [LOWER] * quarter + [UPPER] * 2 * quarter + [LOWER] * quarter,
            ChannelName.PULSE2: [UPPER] * quarter + [LOWER] * 2 * quarter + [UPPER] * quarter,
        }

        judgment = _judged(written_truth(INTERVAL), converted(played))

        assert judgment.components[HANDOVERS] == 2.0
        assert judgment.score == 2.0

    def test_a_silent_conversion_holds_no_extra_fragment(self) -> None:
        judgment = _judged(
            written_truth({ChannelName.TRIANGLE: BASS}), converted({ChannelName.TRIANGLE: [SILENT_TRIANGLE] * FRAMES})
        )

        assert (judgment.score, judgment.components[FRAGMENTS]) == (0.0, 0.0)

    @pytest.mark.xfail(
        strict=True, reason="suspected bug: a silent note pulls the mean fragments under one and hides another's"
    )
    def test_a_dropped_note_offsets_another_note_s_extra_fragment(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": (LOW_NOTE,) * 4 + (HIGH_NOTE,) * 4})
        low = TriangleInstruction(on=True, pitch=57)
        high = TriangleInstruction(on=True, pitch=69)
        with_a_dropout = [low, low, SILENT_TRIANGLE, low]
        answered = _judged(truth, converted({ChannelName.TRIANGLE: with_a_dropout + [high] * 4}))
        dropped = _judged(truth, converted({ChannelName.TRIANGLE: with_a_dropout + [SILENT_TRIANGLE] * 4}))

        assert dropped.score >= answered.score

    def test_a_sound_of_no_note_is_left_unjudged(self) -> None:
        truth = Truth(instructions={}, pitches={})

        assert ContinuityReferee().judge(truth, converted({ChannelName.TRIANGLE: BASS})) is None
