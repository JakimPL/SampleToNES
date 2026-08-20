from typing import Dict, Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.builder import (
    channel_instructions,
    song_from_reconstruction,
    streams_from_instructions,
)
from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.specification.registers import (
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SOUNDING_RELOAD,
)
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_REFERENCE_PITCH,
    PLAYER_TIMER_TABLE,
    player_reconstruction,
    silent_pulse,
    sounding_pulse,
)

NTSC_FREQUENCY: Final[int] = 60
HALF_RATE_FREQUENCY: Final[int] = 30
SOUNDING_TICKS: Final[int] = 4
BASS_PITCH: Final[int] = 45
NOISE_PERIOD: Final[int] = 10
NOISE_VOLUME: Final[int] = 8


def melody() -> List[InstructionUnion]:
    return [sounding_pulse(PLAYER_REFERENCE_PITCH, PLAYER_FULL_VOLUME, 0) for _ in range(SOUNDING_TICKS)]


def one_channel(generator: ChannelName) -> Dict[ChannelName, List[InstructionUnion]]:
    return {generator: melody()}


class TestChannelInstructions:
    """A channel's stream read as the instruction type its encoder takes."""

    def test_a_stream_of_the_channels_own_type_passes_through(self) -> None:
        instructions = melody()
        assert channel_instructions(instructions, PulseInstruction) == instructions

    def test_a_channel_describing_no_frame_rests_for_a_tick(self) -> None:
        assert channel_instructions([], PulseInstruction) == [PulseInstruction.null_instruction()]

    def test_a_resting_channel_rests_in_its_own_type(self) -> None:
        assert channel_instructions([], NoiseInstruction) == [NoiseInstruction.null_instruction()]

    def test_a_stream_of_another_channels_type_raises(self) -> None:
        with pytest.raises(TypeError):
            channel_instructions(melody(), TriangleInstruction)


class TestStreamsFromInstructions:
    """The four channels encoded together, each through the encoder its own type names."""

    def test_a_sounding_channel_carries_a_tick_per_instruction_and_a_release(self) -> None:
        streams = streams_from_instructions(one_channel(ChannelName.PULSE1), PLAYER_TIMER_TABLE)
        assert len(streams.pulse1) == SOUNDING_TICKS + 1

    def test_a_channel_describing_no_frame_carries_a_single_tick(self) -> None:
        streams = streams_from_instructions(one_channel(ChannelName.PULSE1), PLAYER_TIMER_TABLE)
        assert (len(streams.pulse2), len(streams.triangle), len(streams.noise)) == (1, 1, 1)

    def test_a_pitch_reaches_the_timer_the_table_states(self) -> None:
        streams = streams_from_instructions(one_channel(ChannelName.PULSE1), PLAYER_TIMER_TABLE)
        timer = PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH]
        assert (streams.pulse1[0].timer_low, streams.pulse1[0].timer_high) == (timer & 0xFF, timer >> 8)

    def test_each_channel_reads_its_own_stream(self) -> None:
        instructions: Dict[ChannelName, List[InstructionUnion]] = {
            ChannelName.PULSE2: melody(),
            ChannelName.TRIANGLE: [TriangleInstruction(on=True, pitch=BASS_PITCH)],
            ChannelName.NOISE: [
                NoiseInstruction(on=True, period=NOISE_PERIOD, volume=NOISE_VOLUME, short=False),
            ],
        }
        streams = streams_from_instructions(instructions, PLAYER_TIMER_TABLE)
        assert len(streams.pulse2) == SOUNDING_TICKS + 1
        assert streams.triangle[0].linear_counter == TRIANGLE_COUNTER_CONTROL | TRIANGLE_SOUNDING_RELOAD
        assert streams.noise[0].control & 0x0F == NOISE_VOLUME

    def test_a_channel_holding_another_channels_instructions_raises(self) -> None:
        instructions: Dict[ChannelName, List[InstructionUnion]] = {ChannelName.TRIANGLE: melody()}
        with pytest.raises(TypeError):
            streams_from_instructions(instructions, PLAYER_TIMER_TABLE)


class TestSongFromReconstruction:
    """A reconstruction read as the song the console plays it as."""

    def test_the_song_lasts_the_ticks_its_longest_channel_covers(self) -> None:
        reconstruction = player_reconstruction(one_channel(ChannelName.PULSE1), NTSC_FREQUENCY)
        assert song_from_reconstruction(reconstruction, loop_tick=None).ticks == SOUNDING_TICKS + 1

    def test_the_schedule_follows_the_rate_the_reconstruction_was_built_at(self) -> None:
        reconstruction = player_reconstruction(one_channel(ChannelName.PULSE1), HALF_RATE_FREQUENCY)
        song = song_from_reconstruction(reconstruction, loop_tick=None)
        assert song.schedule == PlaySchedule.from_parameters(HALF_RATE_FREQUENCY)

    def test_the_song_carries_the_loop_it_is_given(self) -> None:
        reconstruction = player_reconstruction(one_channel(ChannelName.PULSE1), NTSC_FREQUENCY)
        assert song_from_reconstruction(reconstruction, loop_tick=0).loop_tick == 0

    def test_a_loop_beyond_the_songs_ticks_raises(self) -> None:
        reconstruction = player_reconstruction(one_channel(ChannelName.PULSE1), NTSC_FREQUENCY)
        with pytest.raises(ValueError):
            song_from_reconstruction(reconstruction, loop_tick=SOUNDING_TICKS + 1)

    def test_the_timers_come_from_the_reconstructions_own_configuration(self) -> None:
        reconstruction = player_reconstruction(one_channel(ChannelName.PULSE1), NTSC_FREQUENCY)
        song = song_from_reconstruction(reconstruction, loop_tick=None)
        timer = get_timer_table(reconstruction.config)[PLAYER_REFERENCE_PITCH]
        assert (song.streams.pulse1[0].timer_low, song.streams.pulse1[0].timer_high) == (timer & 0xFF, timer >> 8)

    def test_a_reconstruction_describing_no_frame_plays_one_resting_tick(self) -> None:
        reconstruction = player_reconstruction({ChannelName.PULSE1: [silent_pulse()]}, NTSC_FREQUENCY)
        song = song_from_reconstruction(reconstruction, loop_tick=None)
        assert song.ticks == 1
