from typing import Final, List, Sequence

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.channel import ChannelPlanes, TonePlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.registers.tone import ToneRegisters
from sampletones_player.specification.binary import unsigned_byte

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
) -> TonePlanes:
    ticks = _tone_ticks(registers)
    indices = [pitches.index(tick.anchor) for tick in ticks]
    return TonePlanes(
        control=bytes(tick.values[CONTROL_VALUE_INDEX] for tick in ticks),
        value=bytes(indices),
        bend=bytes(unsigned_byte(tick.divider - pitches.timers[index]) for tick, index in zip(ticks, indices)),
    )


def _noise_planes(registers: Sequence[ChannelRegisters]) -> ChannelPlanes:
    control = bytes(tick.values[CONTROL_VALUE_INDEX] for tick in registers)
    value = bytes(tick.values[FIRST_VALUE_INDEX] for tick in registers)
    return ChannelPlanes(control=control, value=value)


def channel_planes(
    channel: ChannelName,
    registers: Sequence[ChannelRegisters],
    pitches: PitchTable,
) -> ChannelPlanes:
    """Separates one channel's ticks into the planes the codec reads.

    A tone channel's value plane names the pitch each divider is counted from, and its bend plane
    the steps from that pitch's own divider, so a note the frame sounds unbent holds a bend of
    nothing.

    Args:
        channel: The channel the registers belong to.
        registers: The channel's per-tick register values.
        pitches: The timer each pitch sounds at.

    Returns:
        ChannelPlanes: The channel's own planes.

    Raises:
        TypeError: If a tone channel's ticks hold registers another channel writes.
        ValueError: If a tone channel's divider lies further from the pitch it is counted from than
            a signed byte states.
    """
    if channel in TONE_CHANNELS:
        return _tone_planes(registers, pitches)

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
    pulse1, pulse2, triangle, noise = streams.padded
    return SongPlanes(
        pulse1=_tone_planes(pulse1, pitches),
        pulse2=_tone_planes(pulse2, pitches),
        triangle=_tone_planes(triangle, pitches),
        noise=_noise_planes(noise),
    )
