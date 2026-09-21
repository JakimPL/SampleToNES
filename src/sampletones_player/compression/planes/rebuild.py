from typing import Iterator, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.flags import is_flagged, pitch_index
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
    value: bytes,
    bend: bytes,
    timers: Tuple[int, ...],
) -> Tuple[int, ...]:
    """The divider each tick of a tone channel reaches, its note and its bend together.

    This is the reading the driver performs between the pitch table and the timer registers,
    stated where it is testable: a flagged tick takes the bend plane's next value, and every
    other tick sounds its pitch's own divider.

    Args:
        value: The pitch each tick names, under the flag saying whether it bends.
        bend: The steps each flagged tick stands from its pitch's own divider.
        timers: The divider each pitch sounds at, in pitch order.

    Returns:
        Tuple[int, ...]: One divider per tick.
    """
    bends = iter(bend)
    return tuple(timers[pitch_index(named)] + (signed_byte(next(bends)) if is_flagged(named) else 0) for named in value)


def _sounded(
    planes: Tuple[bytes, ...],
    pitches: PitchTable,
) -> Iterator[Tuple[int, int, int]]:
    """Each tick's control byte, the divider its registers carry, and the pitch it is counted from."""
    control, value, bend = planes
    yield from zip(
        control,
        tone_dividers(value, bend, pitches.timers),
        (pitches.pitch(pitch_index(named)) for named in value),
    )


def _pulse_registers(
    planes: Tuple[bytes, ...],
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
    planes: Tuple[bytes, ...],
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


def _noise_registers(planes: Tuple[bytes, ...]) -> Tuple[NoiseRegisters, ...]:
    control, value = planes
    return tuple(
        NoiseRegisters(
            control=timbre,
            period=period,
        )
        for timbre, period in zip(control, value)
    )


def streams_from_planes(
    planes: SongPlanes,
    pitches: PitchTable,
) -> ChannelStreams:
    """Rebuilds a song's four streams from the planes they were separated into.

    Args:
        planes: Every plane, in the order the song block writes them.
        pitches: The timer each pitch sounds at.

    Returns:
        ChannelStreams: The per-tick register values every channel plays.
    """
    return ChannelStreams(
        pulse1=_pulse_registers(planes.of(ChannelName.PULSE1), pitches),
        pulse2=_pulse_registers(planes.of(ChannelName.PULSE2), pitches),
        triangle=_triangle_registers(planes.of(ChannelName.TRIANGLE), pitches),
        noise=_noise_registers(planes.of(ChannelName.NOISE)),
    )
