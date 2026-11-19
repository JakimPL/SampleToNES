from typing import Dict, Final, List

import pytest
from pydantic import ValidationError

from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.corpus.written import (
    SINGLE_STEM_ID,
    WRITTEN_COEFFICIENT,
    FrameRun,
    channel_frames,
    single_recording_record,
    written_reconstruction,
    written_runs,
)

SCALE: Final[float] = 0.5
COEFFICIENT: Final[float] = 0.75
FRAMES: Final[Dict[ChannelName, List[InstructionUnion]]] = {
    ChannelName.PULSE1: [
        PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=2),
        PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=2),
        PulseInstruction(on=True, pitch=62, volume=9, duty_cycle=1),
    ]
}
PULSE_FRAME: Final = PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=2)
REST_FRAME: Final = PulseInstruction(on=False, pitch=60, volume=0, duty_cycle=2)


class TestChannelFrames:
    def test_each_run_repeats_its_frame_in_order(self) -> None:
        runs = [
            FrameRun(count=2, frame=PULSE_FRAME.model_dump()),
            FrameRun(count=1, frame=REST_FRAME.model_dump()),
        ]

        assert channel_frames(ChannelName.PULSE1, runs) == [PULSE_FRAME, PULSE_FRAME, REST_FRAME]

    def test_a_frame_is_read_as_the_instruction_its_channel_takes(self) -> None:
        triangle = channel_frames(ChannelName.TRIANGLE, [FrameRun(count=1, frame={"on": True, "pitch": 48})])
        noise = channel_frames(
            ChannelName.NOISE,
            [FrameRun(count=1, frame={"on": True, "period": 3, "volume": 9, "short": True})],
        )

        assert triangle == [TriangleInstruction(on=True, pitch=48)]
        assert noise == [NoiseInstruction(on=True, period=3, volume=9, short=True)]

    def test_a_frame_the_channel_cannot_play_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            channel_frames(ChannelName.NOISE, [FrameRun(count=1, frame=PULSE_FRAME.model_dump())])


class TestSingleRecordingRecord:
    def test_a_sounding_frame_answers_to_the_recording_and_a_silent_one_to_rest(self) -> None:
        record = single_recording_record(FRAMES, SCALE)

        assert [(assignment.channel_name, assignment.stem_ids) for assignment in record.assignments] == [
            (ChannelName.PULSE1, (SINGLE_STEM_ID, RESTING_STEM_ID, SINGLE_STEM_ID))
        ]
        assert record.scale == SCALE


class TestWrittenReconstruction:
    def test_the_reconstruction_plays_the_frames_it_is_given_and_names_no_recording(self) -> None:
        reconstruction = written_reconstruction(
            FRAMES,
            coefficient=COEFFICIENT,
            scale=SCALE,
            audio_filepath=(),
        )

        assert list(reconstruction.instructions[ChannelName.PULSE1]) == FRAMES[ChannelName.PULSE1]
        assert reconstruction.playing_channels == (ChannelName.PULSE1,)
        assert reconstruction.coefficient == COEFFICIENT
        assert not reconstruction.stems_data.sources


class TestWrittenRuns:
    def test_each_channel_plays_its_runs_at_unit_level_with_no_recording(self) -> None:
        reconstruction = written_runs({ChannelName.PULSE2: [FrameRun(count=3, frame=PULSE_FRAME.model_dump())]})

        assert reconstruction.playing_channels == (ChannelName.PULSE2,)
        assert list(reconstruction.instructions[ChannelName.PULSE2]) == [PULSE_FRAME] * 3
        assert reconstruction.coefficient == WRITTEN_COEFFICIENT
        assert not reconstruction.stems_data.sources
