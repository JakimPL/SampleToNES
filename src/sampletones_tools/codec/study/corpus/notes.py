from typing import Final, List, Mapping, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import PulseExporter, TriangleExporter
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_player.registers.channel import channel_instructions
from sampletones_player.registers.hold import hold

TONE_ORDER: Final[Tuple[ChannelName, ...]] = (
    ChannelName.PULSE1,
    ChannelName.PULSE2,
    ChannelName.TRIANGLE,
)


def channel_notes(
    channel: ChannelName,
    instructions: Sequence[InstructionUnion],
) -> bytes:
    """The note each tick of a tone channel names, held the way its registers hold the divider.

    The encoders write a tick per frame and close a sounding stream with one silent tick, and a
    rest holds the note the channel last sounded, so this reads the same ticks the channel's
    registers cover.

    Args:
        channel: The tone channel.
        instructions: The channel's stream.

    Returns:
        bytes: One note per tick the channel's registers cover.

    Raises:
        ValueError: If the channel names no note.
    """
    pitches: List[int]
    volumes: List[int]
    match channel:
        case ChannelName.PULSE1 | ChannelName.PULSE2:
            _, pitches, volumes, _ = PulseExporter.extract_data(channel_instructions(instructions, PulseInstruction))
        case ChannelName.TRIANGLE:
            _, pitches, volumes = TriangleExporter.extract_data(channel_instructions(instructions, TriangleInstruction))
        case _:
            raise ValueError(f"the {channel.value} channel names no note")

    return bytes(hold(pitches, tick) for tick in range(len(volumes)))


def song_notes(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    ticks: int,
) -> Tuple[bytes, ...]:
    """The note each tick of every tone channel names, carried to the song's length.

    A channel running out early holds its final note through the ticks that remain, as its
    registers do.

    Args:
        instructions: The stream each channel carries.
        ticks: The ticks the song lasts.

    Returns:
        Tuple[bytes, ...]: One run of notes per tone channel, in channel order.
    """
    notes = (channel_notes(channel, instructions.get(channel, ())) for channel in TONE_ORDER)
    return tuple(bytes(hold(channel, tick) for tick in range(ticks)) for channel in notes)
