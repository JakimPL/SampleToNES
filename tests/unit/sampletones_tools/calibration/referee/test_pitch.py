from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.pitch import CENTS, OCTAVE, SEMITONE, SILENT, WRONG, PitchReferee
from sampletones_tools.calibration.referee.protocol import Judgment

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 4
BASS_NOTE: Final[int] = 45
BASS: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=BASS_NOTE)] * FRAMES


def _triangle(pitch: int) -> List[InstructionUnion]:
    return [TriangleInstruction(on=True, pitch=pitch)] * FRAMES


def _judged(truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(PitchReferee().judge(truth, reconstruction))


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

    def test_a_synthesized_line_is_read_from_its_frequencies(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES})

        assert _judged(truth, converted({ChannelName.TRIANGLE: _triangle(57)})).score == 0.0

    def test_a_sound_of_no_line_is_left_unjudged(self) -> None:
        hiss = [NoiseInstruction(on=True, period=6, volume=10, short=False)] * FRAMES

        assert (
            PitchReferee().judge(written_truth({ChannelName.NOISE: hiss}), converted({ChannelName.NOISE: hiss})) is None
        )
