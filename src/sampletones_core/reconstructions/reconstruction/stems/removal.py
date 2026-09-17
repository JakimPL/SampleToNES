from pathlib import Path
from typing import Dict, FrozenSet, List, Sequence, Tuple

from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy


def without_stem(reconstruction: Reconstruction, stem_id: int) -> Reconstruction:
    """The reconstruction with one recording taken out, the frames it held left resting.

    A released frame states silence and takes ``RESTING_STEM_ID``, which is the shape a capped
    run already records for a frame every stem passed over. A channel the removal empties stands
    by, describing no frame at all. The frames of the recordings that stay keep their
    instructions and their owners, and the audio the document answers with is read afresh from
    what remains.

    The entry leaves the recorded setup, taking its level along once that level holds nothing
    else, and its source path leaves ``audio_filepath`` from the position it stood at. The
    identifier, configuration, coefficient and metadata carry over, so the result is the same
    document holding one recording fewer.

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
    assignments = [_released_assignment(item, released[item.channel_name]) for item in stems_data.assignments]
    resting = _emptied_channels(assignments, released)

    streams = _released_streams(reconstruction, released, resting)

    return Reconstruction(
        metadata=reconstruction.metadata,
        id=reconstruction.id,
        audio_filepath=_paths_without(reconstruction.audio_filepath, _position_of(config, stem_id)),
        config=reconstruction.config,
        instructions_data=[streams[channel_name] for channel_name in ChannelName.items()],
        stems_data=StemsData(
            config=_config_without(config, stem_id),
            assignments=[item for item in assignments if item.channel_name not in resting],
        ),
        coefficient=reconstruction.coefficient,
    )


def _position_of(config: StemsConfig, stem_id: int) -> int:
    """Where the entry stands among the recorded ones, which is the source path it pairs with."""
    return [entry.id for entry in config.entries].index(stem_id)


def _config_without(config: StemsConfig, stem_id: int) -> StemsConfig:
    """The recorded setup with one entry gone, and the level it emptied gone along with it."""
    levels = [[held for held in level if held != stem_id] for level in config.hierarchy.levels]
    return StemsConfig(
        entries=[entry for entry in config.entries if entry.id != stem_id],
        hierarchy=StemsHierarchy(
            levels=[level for level in levels if level],
            mode=config.hierarchy.mode,
        ),
    )


def _paths_without(paths: Tuple[Path, ...], position: int) -> Tuple[Path, ...]:
    """The recorded source paths with the one at ``position`` gone, empty staying empty."""
    return tuple(path for index, path in enumerate(paths) if index != position)


def _released_assignment(item: ChannelAssignment, released: Sequence[bool]) -> ChannelAssignment:
    """The channel's per-frame ownership with each released frame resting."""
    return ChannelAssignment(
        channel_name=item.channel_name,
        stem_ids=[RESTING_STEM_ID if frame_released else held for held, frame_released in zip(item.stem_ids, released)],
    )


def _emptied_channels(
    assignments: Sequence[ChannelAssignment],
    released: Dict[ChannelName, List[bool]],
) -> FrozenSet[ChannelName]:
    """The channels the removal leaves resting through every frame.

    A channel reaches this state by losing frames it held, so one that already rested
    throughout is left as it stood.
    """
    return frozenset(
        item.channel_name
        for item in assignments
        if any(released[item.channel_name]) and all(held == RESTING_STEM_ID for held in item.stem_ids)
    )


def _released_streams(
    reconstruction: Reconstruction,
    released: Dict[ChannelName, List[bool]],
    resting: FrozenSet[ChannelName],
) -> Dict[ChannelName, InstructionsItem]:
    """Every channel's stream as the removal leaves it, keyed by channel.

    A channel the removal empties stands by, one it reaches states silence where the recording
    held a frame, and one it reaches none of stands exactly as it did.
    """
    streams: Dict[ChannelName, InstructionsItem] = {}
    for channel_name, stream in reconstruction.streams.items():
        if channel_name in resting:
            streams[channel_name] = InstructionsItem.resting(channel_name)
        elif channel_name in released:
            streams[channel_name] = _released_stream(stream, released[channel_name])
        else:
            streams[channel_name] = stream

    return streams


def _released_stream(stream: InstructionsItem, released: Sequence[bool]) -> InstructionsItem:
    """The channel's stream with each released frame stating silence.

    The silent instruction takes the type the stream already carries, which is the type the
    channel is read through, so the stream stays one exporter's throughout.
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
