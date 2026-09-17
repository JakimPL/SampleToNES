from typing import Dict, Mapping, Sequence

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData

StemDrives = Mapping[int, Mapping[ChannelName, float]]


def frame_drive(
    drives: StemDrives,
    stem_id: int,
    channel_name: ChannelName,
) -> float:
    """The drive the stem owning a frame gives the channel.

    A frame no recording holds plays at unit drive, which is the level its silence stands at and
    the level a frame the reader wrote sounds at. A recording that states a drive for a channel
    plays it at that drive, and one that states none plays it as the library is calibrated,
    which is the reading a setup written before drives existed carries.

    Args:
        drives: The drive each recorded stem gives each channel it occupies.
        stem_id: The stem holding the frame.
        channel_name: The channel the frame belongs to.

    Returns:
        float: The factor the frame's rendering is scaled by.
    """
    return drives.get(stem_id, {}).get(channel_name, UNIT_DRIVE)


def stem_drives(stems_data: StemsData) -> Dict[int, Dict[ChannelName, float]]:
    """The drive each recorded stem gives each channel it occupies, keyed by stem id."""
    return {entry.id: dict(entry.settings.drives) for entry in stems_data.config.entries}


def render_stream(
    instructions: Sequence[InstructionUnion],
    stem_ids: Sequence[int],
    channel_name: ChannelName,
    config: Config,
    drives: StemDrives,
) -> np.ndarray:
    """One channel's audio: its whole stream rendered, each frame at its owner's drive.

    The stream is rendered end to end so each frame continues the oscillator the one before it
    left running, and the drive is applied to the samples a frame already rendered, so the level
    a recording is pushed at reaches the mix without moving the waveform underneath it.

    Args:
        instructions: The channel's instructions, one per frame.
        stem_ids: The stem holding each of those frames.
        channel_name: The channel the stream drives.
        config: The configuration the frames are rendered at.
        drives: The drive each recorded stem gives each channel it occupies.

    Returns:
        np.ndarray: The channel's waveform, one frame per instruction.
    """
    rendered = render_instructions(instructions, channel_name, config)
    frame_length = config.library.frame_length
    for position, stem_id in enumerate(stem_ids):
        drive = frame_drive(drives, stem_id, channel_name)
        if drive != UNIT_DRIVE:
            rendered[position * frame_length : (position + 1) * frame_length] *= drive

    return rendered


def render_streams(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    stems_data: StemsData,
    config: Config,
) -> Dict[ChannelName, np.ndarray]:
    """The audio of every channel that describes a frame, in channel order.

    This is the one reading a reconstruction's sound comes from: the waveform a reader sees,
    what playback sends to the device, what an export writes and what the mixed approximation
    sums. A channel standing by describes no frame and answers with none.

    Args:
        instructions: The instructions each channel is driven by.
        stems_data: The record naming the stem holding each frame.
        config: The configuration the frames are rendered at.

    Returns:
        Dict[ChannelName, np.ndarray]: The waveform each sounding channel renders to.
    """
    drives = stem_drives(stems_data)
    owners = stems_data.assignments_by_channel
    return {
        channel_name: render_stream(
            instructions[channel_name],
            owners.get(channel_name, ()),
            channel_name,
            config,
            drives,
        )
        for channel_name in ChannelName.items()
        if instructions.get(channel_name)
    }
