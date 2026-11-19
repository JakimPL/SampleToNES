from typing import Dict, Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.corpus.midi import read_midi
from sampletones_tools.calibration.corpus.nesmdb import nesmdb_frames

from ..midifiles import nesmdb_piece

RATE: Final[int] = 60


@pytest.fixture(name="frames", scope="module")
def frames_fixture() -> Dict[ChannelName, List[InstructionUnion]]:
    return nesmdb_frames(read_midi(nesmdb_piece()), start_frame=0, frames=RATE, rate=RATE)


class TestNesmdbFrames:
    def test_a_pulse_starts_at_its_velocity_and_moves_with_the_volume_controller(
        self,
        frames: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        pulse = frames[ChannelName.PULSE1]

        assert pulse[0] == PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=1)
        assert pulse[RATE - 1] == PulseInstruction(on=True, pitch=69, volume=6, duty_cycle=1)

    def test_the_triangle_plays_an_octave_above_the_pitch_it_sounds(
        self,
        frames: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        assert frames[ChannelName.TRIANGLE][0] == TriangleInstruction(on=True, pitch=57)

    def test_the_noise_counts_its_periods_from_the_lowest_and_takes_its_mode(
        self,
        frames: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        noise = frames[ChannelName.NOISE]

        assert noise[0] == NoiseInstruction(on=True, period=3, volume=9, short=True)
        assert not noise[RATE // 2].on

    def test_a_window_starts_where_it_is_asked_to(self) -> None:
        late = nesmdb_frames(read_midi(nesmdb_piece()), start_frame=RATE // 2, frames=2, rate=RATE)

        pulse = late[ChannelName.PULSE1][0]
        assert isinstance(pulse, PulseInstruction) and pulse.volume == 6
