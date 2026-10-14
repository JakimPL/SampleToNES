from typing import Optional

import numpy as np

from sampletones_core.audio import silence
from sampletones_core.instructions import InstructionUnion

from .protocol import ChannelGeneratorProtocol


def synthesize_tick(
    generator: ChannelGeneratorProtocol,
    instruction: Optional[InstructionUnion],
    frame_length: int,
) -> np.ndarray:
    """The audio one channel sounds for one tick of ``frame_length`` samples.

    The generator renders the instruction and keeps its timer phase for the next tick, so a note held over
    many ticks sounds one continuous waveform. A channel resting this tick sounds silence and leaves its
    generator where it stood.

    Args:
        generator: The channel's generator.
        instruction: What the channel sounds this tick, or ``None`` where it rests.
        frame_length: The samples the tick spans, as the tick clock gives it.
    """
    if instruction is None:
        return silence(frame_length)

    generator.frame_length = frame_length
    return generator(instruction, save=True)
