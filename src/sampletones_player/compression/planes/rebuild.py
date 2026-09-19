from typing import Iterator, Tuple

from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.channel import ChannelPlanes, TonePlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.registers.triangle import TriangleRegisters
from sampletones_player.specification.binary import signed_byte
from sampletones_player.specification.registers import (
    MAX_REGISTER_VALUE,
    TIMER_HIGH_SHIFT,
)


def tone_dividers(
    planes: TonePlanes,
    timers: Tuple[int, ...],
) -> Tuple[int, ...]:
    """The divider each tick of a tone channel reaches, its note and its bend together.

    This is the reading the driver performs between the pitch table and the timer registers,
    stated where it is testable.

    Args:
        planes: The channel's planes.
        timers: The divider each pitch sounds at, in pitch order.

    Returns:
        Tuple[int, ...]: One divider per tick.
    """
    return tuple(timers[index] + signed_byte(bend) for index, bend in zip(planes.value, planes.bend))


def _sounded(
    planes: TonePlanes,
    pitches: PitchTable,
) -> Iterator[Tuple[int, int, int]]:
    """Each tick's control byte, the divider its registers carry, and the pitch it is counted from."""
    yield from zip(
        planes.control,
        tone_dividers(planes, pitches.timers),
        (pitches.pitch(index) for index in planes.value),
    )


def _pulse_registers(
    planes: TonePlanes,
    pitches: PitchTable,
) -> Tuple[PulseRegisters, ...]:
    return tuple(
        PulseRegisters(
            control=control,
            timer_low=timer & MAX_REGISTER_VALUE,
            timer_high=timer >> TIMER_HIGH_SHIFT,
            anchor=anchor,
        )
        for control, timer, anchor in _sounded(planes, pitches)
    )


def _triangle_registers(
    planes: TonePlanes,
    pitches: PitchTable,
) -> Tuple[TriangleRegisters, ...]:
    return tuple(
        TriangleRegisters(
            linear_counter=control,
            timer_low=timer & MAX_REGISTER_VALUE,
            timer_high=timer >> TIMER_HIGH_SHIFT,
            anchor=anchor,
        )
        for control, timer, anchor in _sounded(planes, pitches)
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
    """Rebuilds a song's four streams from the planes they were separated into.

    Args:
        planes: The planes under the channel each belongs to.
        pitches: The timer each pitch sounds at.

    Returns:
        ChannelStreams: The per-tick register values every channel plays.
    """
    return ChannelStreams(
        pulse1=_pulse_registers(planes.pulse1, pitches),
        pulse2=_pulse_registers(planes.pulse2, pitches),
        triangle=_triangle_registers(planes.triangle, pitches),
        noise=_noise_registers(planes.noise),
    )
