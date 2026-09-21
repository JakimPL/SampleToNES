from typing import Final, List, Sequence, Tuple

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.flags import (
    flagged_value,
    is_flagged,
    note_flags,
)
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.registers.tone import ToneRegisters
from sampletones_player.specification.binary import unsigned_byte
from sampletones_player.specification.planes import SILENT_PITCH_INDEX
from sampletones_player.specification.registers import TRIANGLE_SOUNDING_RELOAD

CONTROL_VALUE_INDEX: Final[int] = 0
FIRST_VALUE_INDEX: Final[int] = 1


def _tone_ticks(registers: Sequence[ChannelRegisters]) -> List[ToneRegisters]:
    ticks: List[ToneRegisters] = []
    for tick in registers:
        match tick:
            case ToneRegisters():
                ticks.append(tick)
            case _:
                raise TypeError(f"a tone channel's planes read tone registers, and a tick holds {type(tick).__name__}")

    return ticks


def _tone_planes(
    registers: Sequence[ChannelRegisters],
    pitches: PitchTable,
) -> Tuple[bytes, ...]:
    ticks = _tone_ticks(registers)
    indices = [pitches.index(tick.anchor) for tick in ticks]
    offsets = [tick.divider - pitches.timers[index] for tick, index in zip(ticks, indices)]
    flags = note_flags(indices, offsets)
    return (
        bytes(tick.values[CONTROL_VALUE_INDEX] for tick in ticks),
        bytes(flagged_value(index, flag) for index, flag in zip(indices, flags)),
        bytes(unsigned_byte(offset) for offset, flag in zip(offsets, flags) if flag),
    )


def _noise_planes(registers: Sequence[ChannelRegisters]) -> Tuple[bytes, ...]:
    return (
        bytes(tick.values[CONTROL_VALUE_INDEX] for tick in registers),
        bytes(tick.values[FIRST_VALUE_INDEX] for tick in registers),
    )


def _triangle_planes(
    registers: Sequence[ChannelRegisters],
    pitches: PitchTable,
) -> Tuple[bytes, ...]:
    """The triangle's planes, its silence named in the pitch its value plane carries.

    The channel sounds at one level, so a tick states whether it sounds through the index it
    names: the index standing above every pitch the table holds silences the linear counter, and
    the divider stays where the channel last sounded. A resting tick names no pitch, so it bends
    nowhere and its bend plane holds nothing for it.
    """
    control, value, bend = _tone_planes(registers, pitches)
    offsets = iter(bend)
    named = bytearray()
    bent = bytearray()
    for timbre, pitch in zip(control, value, strict=True):
        sounding = bool(timbre & TRIANGLE_SOUNDING_RELOAD)
        flagged = is_flagged(pitch)
        offset = next(offsets) if flagged else None
        named.append(pitch if sounding else SILENT_PITCH_INDEX)
        if sounding and offset is not None:
            bent.append(offset)

    return (bytes(named), bytes(bent))


def channel_planes(
    channel: ChannelName,
    registers: Sequence[ChannelRegisters],
    pitches: PitchTable,
) -> Tuple[bytes, ...]:
    """Separates one channel's ticks into the planes the codec reads.

    A tone channel's value plane names the pitch each divider is counted from, and its bend plane
    the steps from that pitch's own divider on the ticks the value flags: each note from its
    first bent tick to its last. A note the frame sounds unbent takes nothing from the bend plane.

    Args:
        channel: The channel the registers belong to.
        registers: The channel's per-tick register values.
        pitches: The timer each pitch sounds at.

    Returns:
        Tuple[bytes, ...]: The channel's own planes, in the order the song block writes them.

    Raises:
        TypeError: If a tone channel's ticks hold registers another channel writes.
        ValueError: If a tone channel's divider lies further from the pitch it is counted from than
            a signed byte states.
    """
    match channel:
        case ChannelName.TRIANGLE:
            return _triangle_planes(registers, pitches)
        case _ if channel in TONE_CHANNELS:
            return _tone_planes(registers, pitches)
        case _:
            return _noise_planes(registers)


def planes_from_streams(
    streams: ChannelStreams,
    pitches: PitchTable,
) -> SongPlanes:
    """Separates a song's four streams into the planes the codec compresses.

    Every channel is carried to the song's full length first, so every plane covers the same
    ticks and the decoder advances them together.

    Args:
        streams: The per-tick register values every channel plays.
        pitches: The timer each pitch sounds at.

    Returns:
        SongPlanes: The planes under the channel each belongs to.

    Raises:
        ValueError: If a tone channel's divider lies further from the pitch it is counted from than
            a signed byte states.
    """
    return SongPlanes(
        planes=PlaneOrder.across(
            plane
            for channel, registers in zip(ChannelName.items(), streams.padded, strict=True)
            for plane in channel_planes(channel, registers, pitches)
        )
    )
