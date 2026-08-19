from typing import Dict, Final, Optional, Sequence

from sampletones_core.constants.general import MAX_PITCH, MIN_PITCH
from sampletones_core.instructions import PulseInstruction
from sampletones_core.timers.arithmetic import frequency_to_timer
from sampletones_player.clock.schedule import PlaySchedule
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.registers.triangle import TriangleRegisters
from sampletones_player.song import Song
from sampletones_player.specification.registers import (
    DUTY_CYCLE_SHIFT,
    MAX_REGISTER_VALUE,
    NOISE_MODE_SHIFT,
    SUSTAINED_LEVEL,
    TIMER_HIGH_SHIFT,
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_SILENT_RELOAD,
    TRIANGLE_SOUNDING_RELOAD,
)
from sampletones_shared.utils.frequencies import pitch_to_frequency

PLAYER_REFERENCE_TIMER: Final[int] = 0x154
PLAYER_OCTAVE_UP_TIMER: Final[int] = PLAYER_REFERENCE_TIMER // 2
PLAYER_REFERENCE_PERIOD: Final[int] = 0x0A
PLAYER_FULL_VOLUME: Final[int] = 15
PLAYER_SILENT_VOLUME: Final[int] = 0


def pulse_tick(
    volume: int,
    duty_cycle: int,
    timer: int,
) -> PulseRegisters:
    """A pulse channel's registers for one tick, spelled the way the encoder spells them."""
    return PulseRegisters(
        control=(duty_cycle << DUTY_CYCLE_SHIFT) | SUSTAINED_LEVEL | volume,
        timer_low=timer & MAX_REGISTER_VALUE,
        timer_high=timer >> TIMER_HIGH_SHIFT,
    )


def triangle_tick(sounding: bool, timer: int) -> TriangleRegisters:
    """A triangle channel's registers for one tick, spelled the way the encoder spells them."""
    reload_value = TRIANGLE_SOUNDING_RELOAD if sounding else TRIANGLE_SILENT_RELOAD
    return TriangleRegisters(
        linear_counter=TRIANGLE_COUNTER_CONTROL | reload_value,
        timer_low=timer & MAX_REGISTER_VALUE,
        timer_high=timer >> TIMER_HIGH_SHIFT,
    )


def noise_tick(
    volume: int,
    mode: int,
    register_period: int,
) -> NoiseRegisters:
    """A noise channel's registers for one tick, its period counted the way ``$400E`` counts it."""
    return NoiseRegisters(
        control=SUSTAINED_LEVEL | volume,
        period=(mode << NOISE_MODE_SHIFT) | register_period,
    )


def player_streams(
    pulse1: Sequence[PulseRegisters],
    pulse2: Sequence[PulseRegisters],
    triangle: Sequence[TriangleRegisters],
    noise: Sequence[NoiseRegisters],
) -> ChannelStreams:
    return ChannelStreams(
        pulse1=tuple(pulse1),
        pulse2=tuple(pulse2),
        triangle=tuple(triangle),
        noise=tuple(noise),
    )


def resting_streams(pulse1: Sequence[PulseRegisters]) -> ChannelStreams:
    """Streams where one pulse channel carries the song and the other three rest on a single tick."""
    return player_streams(
        pulse1=pulse1,
        pulse2=(pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER),),
        triangle=(triangle_tick(False, PLAYER_REFERENCE_TIMER),),
        noise=(noise_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_PERIOD),),
    )


def player_song(
    streams: ChannelStreams,
    nes_frequency: int,
    loop_tick: Optional[int],
) -> Song:
    return Song(
        streams=streams,
        schedule=PlaySchedule.from_parameters(nes_frequency),
        loop_tick=loop_tick,
    )


PLAYER_TIMER_TABLE: Final[Dict[int, int]] = {
    pitch: frequency_to_timer(pitch_to_frequency(pitch)) for pitch in range(MIN_PITCH, MAX_PITCH + 1)
}
PLAYER_REFERENCE_PITCH: Final[int] = 69
PLAYER_PULSE_TIMER_MUTE_FLOOR: Final[int] = 8


def sounding_pulse(
    pitch: int,
    volume: int,
    duty_cycle: int,
) -> PulseInstruction:
    return PulseInstruction(
        on=True,
        pitch=pitch,
        volume=volume,
        duty_cycle=duty_cycle,
    )


def silent_pulse() -> PulseInstruction:
    return PulseInstruction.null_instruction()
