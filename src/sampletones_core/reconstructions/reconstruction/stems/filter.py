from typing import AbstractSet, Dict, List, Mapping, Sequence

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.ownership import heard_frame
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


def filter_approximations(
    stems_data: StemsData,
    approximations: Mapping[ChannelName, np.ndarray],
    selection: StemSelection,
    frame_length: int,
) -> Dict[ChannelName, np.ndarray]:
    """Returns the per-channel approximations with the unselected stems' frames zeroed.

    Stem id ``i`` names frame ``i`` of its channel — the same index the channel's stored
    approximation slices hold — so a frame whose stem is unselected on that channel becomes
    silence while every other frame keeps its samples. The selection answers each channel on
    its own, so one recording is heard on a channel and stays quiet on the next. The arrays
    keep their lengths, which is what aligns a filtered mix with the unfiltered one sample for
    sample. The mask covers the frames the stored array holds; samples past the last recorded
    frame keep their values.
    """
    filtered: Dict[ChannelName, np.ndarray] = {}
    for channel, stem_ids in stems_data.assignments_by_channel.items():
        approximation = approximations[channel]
        keep = np.isin(np.array(stem_ids, dtype=int), list(selection.stems_for(channel)))
        keep_samples = np.repeat(keep, frame_length)
        masked = np.array(approximation, copy=True)
        masked[~keep_samples[: len(masked)]] = 0
        filtered[channel] = masked

    return filtered


def heard_instructions(
    stems_data: StemsData,
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    selection: StemSelection,
) -> Dict[ChannelName, List[InstructionUnion]]:
    """The part of each channel's stream the recordings a reader hears account for.

    A frame held by a recording the reader left out reads as its channel's silent instruction
    at the index it stands on, so the reading lines up with the audio and the record frame for
    frame. The reading ends at the last frame the reader hears, so a channel every recording is
    left out on reads as standing by, while a channel the reader hears keeps every frame it
    describes — which is the count an export writes and a footprint measures.

    Args:
        stems_data: The record naming the stem holding each frame.
        instructions: The stream each channel plays.
        selection: The recordings the reader hears, channel by channel.

    Returns:
        Dict[ChannelName, List[InstructionUnion]]: The heard part of each channel's stream.
    """
    heard: Dict[ChannelName, List[InstructionUnion]] = {}
    for channel_name, stream in instructions.items():
        stem_ids = stems_data.assignments_by_channel.get(channel_name, ())
        hearing = selection.stems_for(channel_name)
        masked = _masked_stream(stream, stem_ids, hearing)
        heard[channel_name] = masked[: _heard_length(stem_ids, len(masked), hearing)]

    return heard


def _masked_stream(
    stream: Sequence[InstructionUnion],
    stem_ids: Sequence[int],
    heard: AbstractSet[int],
) -> List[InstructionUnion]:
    """The stream with every frame outside the reader's hearing stating silence in its place."""
    if not stream:
        return list(stream)

    null: InstructionUnion = type(stream[0]).null_instruction()
    return [instruction if _is_heard(stem_ids, frame, heard) else null for frame, instruction in enumerate(stream)]


def _is_heard(stem_ids: Sequence[int], frame: int, heard: AbstractSet[int]) -> bool:
    """Whether the reader hears one frame, which a frame standing past the record always is."""
    if frame >= len(stem_ids):
        return True

    return heard_frame(stem_ids[frame], heard)


def _heard_length(stem_ids: Sequence[int], frames: int, heard: AbstractSet[int]) -> int:
    """How far a stream runs to the last frame the reader hears.

    A channel is in play for as long as its stream describes a frame, so what the reading may
    let go of is the stretch the reader hears nothing of — the tail a recording left out held.
    A frame the reader hears stands however quietly it sounds, which keeps this reading and the
    document's own count of the channel at one answer.
    """
    for frame in reversed(range(frames)):
        if _is_heard(stem_ids, frame, heard):
            return frame + 1

    return 0
