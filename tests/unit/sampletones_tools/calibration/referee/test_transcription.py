from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.protocol import SCORE_READING, Judgment
from sampletones_tools.calibration.referee.transcription import (
    DUTY,
    MISSED,
    MODE,
    NOTE,
    PERIOD,
    SPURIOUS,
    VOLUME,
    TranscriptionReferee,
)

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 4
TOLERANCE: Final[int] = 1
LEAD: Final[List[InstructionUnion]] = [PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=2)] * FRAMES
HARMONY: Final[List[InstructionUnion]] = [PulseInstruction(on=True, pitch=64, volume=8, duty_cycle=1)] * FRAMES
BASS: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=45)] * FRAMES
HISS: Final[List[InstructionUnion]] = [NoiseInstruction(on=True, period=6, volume=10, short=False)] * FRAMES
SILENT_PULSE: Final[List[InstructionUnion]] = [PulseInstruction(on=False, pitch=69, volume=0, duty_cycle=2)] * FRAMES


@pytest.fixture(name="referee")
def referee_fixture() -> TranscriptionReferee:
    return TranscriptionReferee(volume_tolerance=TOLERANCE)


def _judged(referee: TranscriptionReferee, truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(referee.judge(truth, reconstruction))


def _pulse(volume: int, duty_cycle: int, pitch: int) -> List[InstructionUnion]:
    return [PulseInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=duty_cycle)] * FRAMES


class TestTranscriptionReferee:
    def test_a_conversion_playing_the_frames_as_written_scores_zero(self, referee: TranscriptionReferee) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS, ChannelName.NOISE: HISS}

        assert _judged(referee, written_truth(written), converted(written)).score == 0.0

    def test_the_pulses_count_as_written_whichever_carries_which_line(self, referee: TranscriptionReferee) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY}
        swapped = {ChannelName.PULSE1: HARMONY, ChannelName.PULSE2: LEAD}

        assert _judged(referee, written_truth(written), converted(swapped)).score == 0.0

    def test_a_silent_conversion_misses_every_written_frame(self, referee: TranscriptionReferee) -> None:
        judgment = _judged(
            referee, written_truth({ChannelName.PULSE1: LEAD}), converted({ChannelName.PULSE1: SILENT_PULSE})
        )

        assert judgment.score == 1.0
        assert judgment.components[MISSED] == 1.0

    def test_a_channel_sounding_where_the_writing_is_silent_counts_as_spurious(
        self,
        referee: TranscriptionReferee,
    ) -> None:
        judgment = _judged(
            referee,
            written_truth({ChannelName.PULSE1: LEAD}),
            converted({ChannelName.PULSE1: LEAD, ChannelName.NOISE: HISS}),
        )

        assert judgment.score == pytest.approx(0.5)
        assert judgment.components[SPURIOUS] == pytest.approx(0.5)
        assert judgment.components[MISSED] == 0.0

    def test_a_volume_within_the_tolerance_plays_as_written(self, referee: TranscriptionReferee) -> None:
        judgment = _judged(
            referee,
            written_truth({ChannelName.PULSE1: LEAD}),
            converted({ChannelName.PULSE1: _pulse(12 - TOLERANCE, 2, 69)}),
        )

        assert judgment.readings()[SCORE_READING] == 0.0

    def test_a_volume_past_the_tolerance_counts_against_the_volume(self, referee: TranscriptionReferee) -> None:
        judgment = _judged(
            referee,
            written_truth({ChannelName.PULSE1: LEAD}),
            converted({ChannelName.PULSE1: _pulse(12 - TOLERANCE - 1, 2, 69)}),
        )

        assert judgment.score == 1.0
        assert (judgment.components[VOLUME], judgment.components[NOTE], judgment.components[DUTY]) == (1.0, 0.0, 0.0)

    def test_every_field_the_noise_takes_is_read(self, referee: TranscriptionReferee) -> None:
        played = [NoiseInstruction(on=True, period=7, volume=10, short=True)] * FRAMES

        judgment = _judged(referee, written_truth({ChannelName.NOISE: HISS}), converted({ChannelName.NOISE: played}))

        assert (judgment.components[PERIOD], judgment.components[MODE], judgment.components[VOLUME]) == (1.0, 1.0, 0.0)

    def test_a_synthesized_sound_written_as_no_frames_is_left_unjudged(self, referee: TranscriptionReferee) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES})

        assert referee.judge(truth, converted({ChannelName.TRIANGLE: BASS})) is None
