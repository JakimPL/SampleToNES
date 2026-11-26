from typing import Dict, Mapping, Sequence

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import CHANNEL_CLASSES, NoiseGenerator, render_on
from sampletones_core.instructions import InstructionUnion, NoiseInstruction


def started_channels(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    config: Config,
    random: np.random.Generator,
) -> Dict[ChannelName, np.ndarray]:
    """Every sounding channel's frames rendered as a conversion naming each frame right plays them.

    A transcription names each frame's note, volume and timbre, and each channel's oscillator runs on
    through the frames. A pulse and the triangle start from their reset phase, as the recording's
    channels do, so a conversion naming their frames right plays the waveform the recording plays,
    the phase between two channels included. The noise's shift register steps through a sequence
    that every earlier frame's period and mode move along, so a conversion missing any of them plays
    another stretch of it from then on. The noise therefore starts from a register value and a clock
    position drawn from ``random``, uniform over the states its first sounding frame may take.

    Args:
        instructions: What each channel plays, one instruction per frame.
        config: The configuration the frames are rendered at.
        random: Where the noise's starting state is drawn from.

    Returns:
        The waveform of each channel sounding a frame, in channel order.
    """
    rendered: Dict[ChannelName, np.ndarray] = {}
    for channel_name in ChannelName.items():
        stream = instructions.get(channel_name, ())
        first = next((instruction for instruction in stream if instruction.on), None)
        if first is None:
            continue

        generator = CHANNEL_CLASSES[channel_name](config, channel_name.value)
        if isinstance(generator, NoiseGenerator) and isinstance(first, NoiseInstruction):
            _start_elsewhere(generator, first, random)

        rendered[channel_name] = render_on(generator, stream)

    return rendered


def _start_elsewhere(generator: NoiseGenerator, first: NoiseInstruction, random: np.random.Generator) -> None:
    """Stand the noise's register at a value drawn from ``random`` on the cycle its first frame ``first`` runs through.

    A value off the cycle of the frame's mode opens the sequence at its start, so the value is drawn
    from that cycle, and the clock from between two of its steps.
    """
    cycle = generator.timer.lfsr_tables[first.short].lfsrs
    generator.timer.lfsr = int(cycle[random.integers(len(cycle))])
    generator.timer.clock = float(random.random())
