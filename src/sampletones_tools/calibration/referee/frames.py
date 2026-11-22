from typing import Dict, Mapping, Optional, Sequence, Sized, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion

Frame = Optional[InstructionUnion]


def channel_streams(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    length: int,
) -> Dict[ChannelName, Tuple[Frame, ...]]:
    """Every channel's first ``length`` frames, ``None`` for each frame of a channel describing none.

    A referee compares two sides frame by frame over every channel, so a channel one side leaves out
    reads as silent there.
    """
    return {
        channel: tuple(instructions[channel][:length]) if instructions.get(channel) else (None,) * length
        for channel in ChannelName.items()
    }


def common_length(*streams: Sized) -> int:
    """The frames every stream given describes, among those describing any, zero where none does.

    A channel a conversion leaves out holds an empty stream, which stands for no frames, so it leaves
    the length to the streams that describe some.
    """
    return min((len(stream) for stream in streams if stream), default=0)


def sounds(frame: Frame) -> bool:
    """Whether a frame sounds its channel."""
    return frame is not None and frame.on
