from typing import Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.protocol import Judgment
from sampletones_tools.calibration.referee.stability import MOVES, TOGGLES, StabilityReferee

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 60
ON: Final[InstructionUnion] = TriangleInstruction(on=True, pitch=45)
OFF: Final[InstructionUnion] = TriangleInstruction(on=False, pitch=45)
UP: Final[InstructionUnion] = TriangleInstruction(on=True, pitch=47)
SECONDS: Final[float] = FRAMES / Config().library.nes_frequency


def _flickering(times: int) -> List[InstructionUnion]:
    stream = [ON] * FRAMES
    for frame in range(times):
        stream[2 * frame + 1] = OFF
    return stream


def _judged(truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(StabilityReferee().judge(truth, reconstruction))


class TestStabilityReferee:
    def test_a_conversion_changing_where_its_sound_does_scores_zero(self) -> None:
        stream = [ON] * (FRAMES // 2) + [UP] * (FRAMES // 2)

        judgment = _judged(written_truth({ChannelName.TRIANGLE: stream}), converted({ChannelName.TRIANGLE: stream}))

        assert judgment.score == 0.0

    def test_every_turn_off_and_back_on_beyond_the_sound_s_own_counts_twice(self) -> None:
        judgment = _judged(
            written_truth({ChannelName.TRIANGLE: [ON] * FRAMES}), converted({ChannelName.TRIANGLE: _flickering(3)})
        )

        assert judgment.components[TOGGLES] == pytest.approx(6 / SECONDS)
        assert judgment.components[MOVES] == 0.0

    def test_a_synthesized_sound_changes_where_its_lines_move_to_another_note(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * (FRAMES // 2) + (123.5,) * (FRAMES // 2)})
        stream = [TriangleInstruction(on=True, pitch=57)] * (FRAMES // 2) + [TriangleInstruction(on=True, pitch=59)] * (
            FRAMES // 2
        )

        assert _judged(truth, converted({ChannelName.TRIANGLE: stream})).score == 0.0
