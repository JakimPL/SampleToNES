from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.balance import BASS_ON_A_PULSE, PULSES, SCALE, TRIANGLE, BalanceReferee
from sampletones_tools.calibration.referee.protocol import Judgment

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 4
BASS: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=57)] * FRAMES
LEAD: Final[List[InstructionUnion]] = [PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=2)] * FRAMES
HARMONY: Final[List[InstructionUnion]] = [PulseInstruction(on=True, pitch=64, volume=8, duty_cycle=1)] * FRAMES


def _judged(truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(BalanceReferee().judge(truth, reconstruction))


class TestBalanceReferee:
    def test_a_conversion_playing_the_sound_as_written_scores_zero_at_unit_scale(self) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS}

        judgment = _judged(written_truth(written), converted(written))

        assert judgment.score == pytest.approx(0.0)
        assert judgment.components[SCALE] == pytest.approx(1.0)
        assert judgment.components[BASS_ON_A_PULSE] == 0.0

    def test_a_bass_line_moved_to_a_pulse_starves_the_triangle(self) -> None:
        moved = [PulseInstruction(on=True, pitch=45, volume=10, duty_cycle=2)] * FRAMES

        judgment = _judged(written_truth({ChannelName.TRIANGLE: BASS}), converted({ChannelName.PULSE1: moved}))

        assert judgment.score == pytest.approx(1.0)
        assert judgment.components[TRIANGLE] == pytest.approx(-1.0)
        assert judgment.components[PULSES] == pytest.approx(1.0)
        assert judgment.components[BASS_ON_A_PULSE] == 1.0

    def test_the_pulses_share_as_one_part_whichever_carries_which_line(self) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY}
        swapped = {ChannelName.PULSE1: HARMONY, ChannelName.PULSE2: LEAD}

        assert _judged(written_truth(written), converted(swapped)).score == pytest.approx(0.0)

    def test_a_synthesized_sound_written_as_no_frames_is_left_unjudged(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES})

        assert BalanceReferee().judge(truth, converted({ChannelName.TRIANGLE: BASS})) is None
