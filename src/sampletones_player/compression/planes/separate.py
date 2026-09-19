from typing import Final, Sequence, Tuple

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_core.timers.nearest import NearestPitch
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.channel import ChannelPlanes, TonePlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.streams import ChannelStreams
from sampletones_player.specification.binary import unsigned_byte
from sampletones_player.specification.registers import TIMER_HIGH_SHIFT

CONTROL_VALUE_INDEX: Final[int] = 0
FIRST_VALUE_INDEX: Final[int] = 1
SECOND_VALUE_INDEX: Final[int] = 2


def _divider(tick: ChannelRegisters) -> int:
    return tick.values[FIRST_VALUE_INDEX] | (tick.values[SECOND_VALUE_INDEX] << TIMER_HIGH_SHIFT)


def _tone_planes(
    registers: Sequence[ChannelRegisters],
    nearest: Tuple[NearestPitch, ...],
) -> TonePlanes:
    control = bytes(tick.values[CONTROL_VALUE_INDEX] for tick in registers)
    named = [nearest[_divider(tick)] for tick in registers]
    return TonePlanes(
        control=control,
        value=bytes(pitch.pitch for pitch in named),
        bend=bytes(unsigned_byte(pitch.offset) for pitch in named),
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

    A tone channel's divider becomes the pitch index lying nearest it and the bend left over,
    so a note the frame sounds unbent holds a bend of nothing.

    Args:
        channel: The channel the registers belong to.
        registers: The channel's per-tick register values.
        pitches: The timer each pitch sounds at.

    Returns:
        ChannelPlanes: The channel's own planes.

    Raises:
        ValueError: If a tone channel sounds a divider lying further from every pitch of the table
            than a signed byte states.
    """
    if channel in TONE_CHANNELS:
        return _tone_planes(registers, pitches.nearest)

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
        ValueError: If a tone channel sounds a divider lying further from every pitch of the table
            than a signed byte states.
    """
    nearest = pitches.nearest
    pulse1, pulse2, triangle, noise = streams.padded
    return SongPlanes(
        pulse1=_tone_planes(pulse1, nearest),
        pulse2=_tone_planes(pulse2, nearest),
        triangle=_tone_planes(triangle, nearest),
        noise=_noise_planes(noise),
    )
