from typing import Dict, Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exports.request import InstrumentExport
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.builder import (
    SONG_START,
    channel_instructions,
    instructions_from_instruments,
    loop_tick_from_instruments,
    song_from_reconstruction,
    song_from_sample,
    streams_from_instructions,
)
from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.specification.registers import (
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SOUNDING_RELOAD,
)
from sampletones_shared.music import Tuning
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_REFERENCE_PITCH,
    PLAYER_TIMER_TABLE,
    player_features,
    player_instrument,
    player_reconstruction,
    player_sample,
    silent_pulse,
    sounding_pulse,
)

NTSC_FREQUENCY: Final[int] = 60
HALF_RATE_FREQUENCY: Final[int] = 30
SOUNDING_TICKS: Final[int] = 4
BASS_PITCH: Final[int] = 45
NOISE_PERIOD: Final[int] = 10
NOISE_VOLUME: Final[int] = 8
RETUNED_A4_FREQUENCY: Final[float] = 432.0


def melody() -> List[InstructionUnion]:
    return [sounding_pulse(PLAYER_REFERENCE_PITCH, PLAYER_FULL_VOLUME, 0) for _ in range(SOUNDING_TICKS)]


def one_channel(generator: ChannelName) -> Dict[ChannelName, List[InstructionUnion]]:
    return {generator: melody()}


def lead(*, loop: bool) -> InstrumentExport:
    return player_instrument(
        "lead",
        ChannelName.PULSE1,
        player_features(SOUNDING_TICKS, PLAYER_REFERENCE_PITCH, duty_cycle=True),
        nes_frequency=NTSC_FREQUENCY,
        loop=loop,
    )


def bass(*, loop: bool) -> InstrumentExport:
    return player_instrument(
        "bass",
        ChannelName.TRIANGLE,
        player_features(SOUNDING_TICKS, BASS_PITCH, duty_cycle=False),
        nes_frequency=NTSC_FREQUENCY,
        loop=loop,
    )


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
        timer = get_timer_table(reconstruction.config.tuning)[PLAYER_REFERENCE_PITCH]
        assert (song.streams.pulse1[0].timer_low, song.streams.pulse1[0].timer_high) == (timer & 0xFF, timer >> 8)

    def test_a_retuned_reconstruction_plays_retuned_timers(self) -> None:
        """The console reaches a pitch through a timer, so a reconstruction built against another
        concert pitch plays the divider that concert pitch names.
        """
        reconstruction = player_reconstruction(one_channel(ChannelName.PULSE1), NTSC_FREQUENCY)
        library = reconstruction.config.library.model_copy(update={"a4_frequency": RETUNED_A4_FREQUENCY})
        retuned = reconstruction.model_copy(
            update={"config": reconstruction.config.model_copy(update={"library": library})}
        )
        timer = get_timer_table(retuned.config.tuning)[PLAYER_REFERENCE_PITCH]
        song = song_from_reconstruction(retuned, loop_tick=None)

        assert timer > PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH]
        assert (song.streams.pulse1[0].timer_low, song.streams.pulse1[0].timer_high) == (timer & 0xFF, timer >> 8)

    def test_a_reconstruction_describing_no_frame_plays_one_resting_tick(self) -> None:
        reconstruction = player_reconstruction({ChannelName.PULSE1: [silent_pulse()]}, NTSC_FREQUENCY)
        song = song_from_reconstruction(reconstruction, loop_tick=None)
        assert song.ticks == 1


class TestInstructionsFromInstruments:
    """An export request's channel slices read back as the instructions the console sounds."""

    def test_a_slice_reaches_its_own_channel(self) -> None:
        instructions = instructions_from_instruments((lead(loop=False), bass(loop=False)))
        assert set(instructions) == {ChannelName.PULSE1, ChannelName.TRIANGLE}

    def test_a_slice_reads_back_as_the_instruction_its_channel_sounds(self) -> None:
        instructions = instructions_from_instruments((lead(loop=False), bass(loop=False)))
        assert all(isinstance(item, PulseInstruction) for item in instructions[ChannelName.PULSE1])
        assert all(isinstance(item, TriangleInstruction) for item in instructions[ChannelName.TRIANGLE])

    def test_a_slice_carries_a_frame_per_envelope_item(self) -> None:
        instructions = instructions_from_instruments((lead(loop=False),))
        assert len(instructions[ChannelName.PULSE1]) == SOUNDING_TICKS

    def test_two_slices_naming_one_channel_raise(self) -> None:
        with pytest.raises(ValueError):
            instructions_from_instruments((lead(loop=False), lead(loop=False)))


class TestLoopTickFromInstruments:
    """Where a request's song returns to once it ends."""

    def test_slices_that_all_repeat_return_to_the_songs_start(self) -> None:
        assert loop_tick_from_instruments((lead(loop=True), bass(loop=True))) == SONG_START

    def test_a_slice_playing_once_ends_the_song(self) -> None:
        assert loop_tick_from_instruments((lead(loop=True), bass(loop=False))) is None

    def test_a_request_carrying_no_slice_ends_the_song(self) -> None:
        assert loop_tick_from_instruments(()) is None


class TestSongFromSample:
    """An export request read as the song the console plays it as."""

    def test_every_slice_sounds_on_the_channel_it_was_reconstructed_for(self) -> None:
        song = song_from_sample(
            player_sample("demo", (lead(loop=False), bass(loop=False)), nes_frequency=NTSC_FREQUENCY)
        )
        assert len(song.streams.pulse1) == SOUNDING_TICKS + 1
        assert song.streams.triangle[0].linear_counter == TRIANGLE_COUNTER_CONTROL | TRIANGLE_SOUNDING_RELOAD
        assert len(song.streams.pulse2) == 1

    def test_the_schedule_follows_the_rate_the_request_states(self) -> None:
        song = song_from_sample(player_sample("demo", (lead(loop=False),), nes_frequency=HALF_RATE_FREQUENCY))
        assert song.schedule == PlaySchedule.from_parameters(HALF_RATE_FREQUENCY)

    def test_a_request_whose_slices_repeat_loops(self) -> None:
        song = song_from_sample(player_sample("demo", (lead(loop=True),), nes_frequency=NTSC_FREQUENCY))
        assert song.loop_tick == SONG_START

    def test_the_timers_come_from_the_tuning_the_request_carries(self) -> None:
        song = song_from_sample(player_sample("demo", (lead(loop=False),), nes_frequency=NTSC_FREQUENCY))
        timer = get_timer_table(Tuning())[PLAYER_REFERENCE_PITCH]
        assert (song.streams.pulse1[0].timer_low, song.streams.pulse1[0].timer_high) == (timer & 0xFF, timer >> 8)

    def test_a_retuned_request_plays_retuned_timers(self) -> None:
        """The console reaches a pitch through a timer, so a request built against another concert
        pitch plays the divider that concert pitch names.
        """
        tuning = Tuning(a4_frequency=RETUNED_A4_FREQUENCY)
        song = song_from_sample(player_sample("demo", (lead(loop=False),), nes_frequency=NTSC_FREQUENCY, tuning=tuning))
        timer = get_timer_table(tuning)[PLAYER_REFERENCE_PITCH]
        assert (song.streams.pulse1[0].timer_low, song.streams.pulse1[0].timer_high) == (timer & 0xFF, timer >> 8)
