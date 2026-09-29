from typing import Dict, List, Sequence

from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment


def without_stem(reconstruction: Reconstruction, stem_id: int) -> Reconstruction:
    """The reconstruction with one recording taken out, the frames it held left resting.

    A released frame states silence and takes ``RESTING_STEM_ID``, which is the shape a capped
    run already records for a frame every stem passed over. A channel the removal leaves resting
    through every frame stands by, describing no frame at all and keeping the reference it was
    shaped from. The frames of the recordings that stay keep their instructions and their owners,
    and the audio the document answers with is read afresh from what remains.

    The entry leaves the recorded setup, taking its level and its recorded source along with
    it, once that level holds nothing else. The ids of the recordings that stay are left alone,
    and the document settles the way every change does, so each recording it names still holds
    a frame. The identifier, configuration, coefficient and metadata carry over, so the result is
    the same document holding one recording fewer.

    Args:
        reconstruction: The reconstruction the recording is taken out of.
        stem_id: The stems entry to remove.

    Returns:
        Reconstruction: A fresh reconstruction holding the recordings that stay.

    Raises:
        ValueError: If ``stem_id`` names no recorded entry, or names the last one standing.
    """
    stems_data = reconstruction.stems_data
    config = stems_data.config
    if stem_id not in config.entries_by_id:
        raise ValueError(f"Stem {stem_id} names no entry of the recorded setup")

    if len(config.entries) == 1:
        raise ValueError("A reconstruction holds at least one stem")

    released = {item.channel_name: [held == stem_id for held in item.stem_ids] for item in stems_data.assignments}
    return reconstruction.rewritten(
        _released_streams(reconstruction, released),
        stems_data.with_assignments(
            [_released_assignment(item, released[item.channel_name]) for item in stems_data.assignments]
        ).without_entries(frozenset({stem_id})),
    )


def _released_assignment(item: ChannelAssignment, released: Sequence[bool]) -> ChannelAssignment:
    """The channel's per-frame ownership with each released frame resting."""
    return ChannelAssignment(
        channel_name=item.channel_name,
        stem_ids=[RESTING_STEM_ID if frame_released else held for held, frame_released in zip(item.stem_ids, released)],
    )


def _released_streams(
    reconstruction: Reconstruction,
    released: Dict[ChannelName, List[bool]],
) -> Dict[ChannelName, InstructionsItem]:
    """Every channel's stream as the removal leaves it, keyed by channel.

    A channel the removal reaches states silence where the recording held a frame, and one it
    reaches none of stands exactly as it did.
    """
    return {
        channel_name: _released_stream(stream, released[channel_name]) if channel_name in released else stream
        for channel_name, stream in reconstruction.streams.items()
    }


def _released_stream(stream: InstructionsItem, released: Sequence[bool]) -> InstructionsItem:
    """The channel's stream with each released frame stating silence.

    The silent instruction takes the type the stream already carries, which is the type the
    channel is read through, so the stream stays one exporter's throughout. The reference and the
    held dimensions stay the stream's own, so a channel the removal silences keeps them.
    """
    instructions = [data.instruction for data in stream.instructions]
    if not instructions:
        return stream

    null: InstructionUnion = type(instructions[0]).null_instruction()
    return InstructionsItem.create(
        channel_name=stream.channel_name,
        instructions=[
            null if index < len(released) and released[index] else instruction
            for index, instruction in enumerate(instructions)
        ],
        initial_pitch=stream.initial_pitch,
        held_features=stream.held_features,
    )
