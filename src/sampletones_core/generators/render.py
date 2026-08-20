from typing import Dict, Mapping, Sequence

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion

from .maps import CHANNEL_CLASSES


def render_instructions(
    instructions: Sequence[InstructionUnion],
    channel_name: ChannelName,
    config: Config,
) -> np.ndarray:
    """One channel's audio, rendered frame by frame from the instructions that drive it.

    Each frame continues the oscillator the one before it left running, so a note held across
    frames sounds as a single tone. An instruction spans `config.frame_length` samples, which is
    what ties the rendered length to the rate the configuration runs at.

    Args:
        instructions: The channel's instructions, one per frame.
        channel_name: The channel the instructions drive.
        config: The configuration the frames are rendered at.

    Returns:
        np.ndarray: The channel's waveform, one frame per instruction.

    Raises:
        ValueError: If the channel describes no frame.
    """
    generator = CHANNEL_CLASSES[channel_name](config, channel_name.value)
    frames = [generator(instruction, save=True) for instruction in instructions]  # type: ignore[arg-type]
    return np.concatenate(frames)


def render_channels(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    config: Config,
) -> Dict[ChannelName, np.ndarray]:
    """The audio of every channel that describes a frame, in channel order.

    A channel standing by renders nothing, so what comes back names the channels that sound and
    the waveform each of them plays.

    Args:
        instructions: The instructions each channel is driven by.
        config: The configuration the frames are rendered at.

    Returns:
        Dict[ChannelName, np.ndarray]: The waveform each sounding channel renders to.
    """
    return {
        channel_name: render_instructions(instructions[channel_name], channel_name, config)
        for channel_name in ChannelName.items()
        if instructions.get(channel_name)
    }
