from typing import Dict, Final, List

from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_tools.corpus.written import (
    SINGLE_STEM_ID,
    single_recording_record,
    written_reconstruction,
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


class TestSingleRecordingRecord:
    def test_a_sounding_frame_answers_to_the_recording_and_a_silent_one_to_rest(self) -> None:
        record = single_recording_record(FRAMES, SCALE)

        assert [(assignment.channel_name, assignment.stem_ids) for assignment in record.assignments] == [
            (ChannelName.PULSE1, [SINGLE_STEM_ID, RESTING_STEM_ID, SINGLE_STEM_ID])
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
