from typing import Tuple

from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.channel import ChannelPlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.registers.triangle import TriangleRegisters
from sampletones_player.specification.registers import (
    MAX_REGISTER_VALUE,
    TIMER_HIGH_SHIFT,
)


def _pulse_registers(
    planes: ChannelPlanes,
    timers: Tuple[int, ...],
) -> Tuple[PulseRegisters, ...]:
    return tuple(
        PulseRegisters(
            control=control,
            timer_low=timers[index] & MAX_REGISTER_VALUE,
            timer_high=timers[index] >> TIMER_HIGH_SHIFT,
        )
        for control, index in zip(planes.control, planes.value)
    )


def _triangle_registers(
    planes: ChannelPlanes,
    timers: Tuple[int, ...],
) -> Tuple[TriangleRegisters, ...]:
    return tuple(
        TriangleRegisters(
            linear_counter=control,
            timer_low=timers[index] & MAX_REGISTER_VALUE,
            timer_high=timers[index] >> TIMER_HIGH_SHIFT,
        )
        for control, index in zip(planes.control, planes.value)
    )


def _noise_registers(planes: ChannelPlanes) -> Tuple[NoiseRegisters, ...]:
    return tuple(
        NoiseRegisters(
            control=control,
            period=period,
        )
        for control, period in zip(planes.control, planes.value)
    )


def streams_from_planes(
    planes: SongPlanes,
    pitches: PitchTable,
) -> ChannelStreams:
    """Rebuilds a song's four streams from the eight planes they were separated into.

    Args:
        planes: The eight planes, two per channel.
        pitches: The timer each pitch sounds at.

    Returns:
        ChannelStreams: The per-tick register values every channel plays.
    """
    timers = pitches.timers
    return ChannelStreams(
        pulse1=_pulse_registers(planes.pulse1, timers),
        pulse2=_pulse_registers(planes.pulse2, timers),
        triangle=_triangle_registers(planes.triangle, timers),
        noise=_noise_registers(planes.noise),
    )
