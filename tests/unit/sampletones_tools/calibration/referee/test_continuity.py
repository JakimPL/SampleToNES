from typing import Final, List

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.continuity import FRAGMENTS, HANDOVERS, ContinuityReferee, note_spans
from sampletones_tools.calibration.referee.protocol import Judgment

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 8
BASS: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=57)] * FRAMES
SILENT_TRIANGLE: Final[InstructionUnion] = TriangleInstruction.null_instruction()
PULSE_BASS: Final[InstructionUnion] = PulseInstruction(on=True, pitch=45, volume=10, duty_cycle=2)
SILENT_PULSE: Final[InstructionUnion] = PulseInstruction.null_instruction()


def _judged(truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(ContinuityReferee().judge(truth, reconstruction))


class TestNoteSpans:
    def test_a_line_splits_into_notes_where_it_changes_pitch_or_falls_silent(self) -> None:
        spans = note_spans((110.0, 110.0, 220.0, None, 220.0))

        assert [(span.start, span.end) for span in spans] == [(0, 2), (2, 3), (4, 5)]


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

    def test_a_sound_of_no_note_is_left_unjudged(self) -> None:
        truth = Truth(instructions={}, pitches={})

        assert ContinuityReferee().judge(truth, converted({ChannelName.TRIANGLE: BASS})) is None
