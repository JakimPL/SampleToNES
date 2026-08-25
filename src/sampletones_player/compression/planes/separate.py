from typing import Dict, Final, Sequence

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.channel import ChannelPlanes, TonePlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.specification.registers import TIMER_HIGH_SHIFT

CONTROL_VALUE_INDEX: Final[int] = 0
FIRST_VALUE_INDEX: Final[int] = 1
SECOND_VALUE_INDEX: Final[int] = 2


def _pitch_indices(
    registers: Sequence[ChannelRegisters],
    indices: Dict[int, int],
) -> bytes:
    try:
        return bytes(
            indices[tick.values[FIRST_VALUE_INDEX] | (tick.values[SECOND_VALUE_INDEX] << TIMER_HIGH_SHIFT)]
            for tick in registers
        )
    except KeyError as error:
        raise ValueError(f"a channel sounds timer {error.args[0]}, which no pitch of the table sounds") from error


def _tone_planes(
    registers: Sequence[ChannelRegisters],
    indices: Dict[int, int],
) -> TonePlanes:
    control = bytes(tick.values[CONTROL_VALUE_INDEX] for tick in registers)
    return TonePlanes(
        control=control,
        value=_pitch_indices(registers, indices),
        bend=bytes(len(registers)),
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

    Args:
        channel: The channel the registers belong to.
        registers: The channel's per-tick register values.
        pitches: The timer each pitch sounds at.

    Returns:
        ChannelPlanes: The channel's own planes.

    Raises:
        ValueError: If a tone channel sounds a timer the pitch table states no index for.
    """
    if channel in TONE_CHANNELS:
        return _tone_planes(registers, pitches.indices)

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
        ValueError: If a tone channel sounds a timer the pitch table states no index for.
    """
    indices = pitches.indices
    pulse1, pulse2, triangle, noise = streams.padded
    return SongPlanes(
        pulse1=_tone_planes(pulse1, indices),
        pulse2=_tone_planes(pulse2, indices),
        triangle=_tone_planes(triangle, indices),
        noise=_noise_planes(noise),
    )
