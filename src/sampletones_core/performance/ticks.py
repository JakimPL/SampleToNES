from typing import Optional, Sequence

from sampletones_core.instructions import InstructionUnion
from sampletones_core.performance.modifiers import apply_modifiers
from sampletones_core.performance.state import ChannelPerformance
from sampletones_core.performance.voice import SampleVoice


def sound_tick(
    performance: ChannelPerformance,
    instructions: Sequence[InstructionUnion],
    *,
    loop: bool,
    voice: SampleVoice,
) -> Optional[InstructionUnion]:
    """The instruction a channel sounds this tick, and the step onto the next one.

    A looping sample wraps around its instructions, so it sustains for as long as rows keep it
    sounding; a one-shot plays each of its instructions once and falls silent past the last.
    Either way the channel moves on a tick, so a sample that has run out keeps counting and a
    row starting a note lands it back at the beginning.

    Args:
        performance: What the channel carries; its tick index moves on.
        instructions: The sounding sample's stream for this channel, holding at least one frame.
        loop: Whether the sample repeats its instructions.
        voice: The reading that fills in the dimensions the instrument leaves to the channel.

    Returns:
        Optional[InstructionUnion]: The instruction to sound, or ``None`` where the sample has
            played out and the channel rests.
    """
    index = performance.tick_index
    performance.tick_index += 1

    if loop:
        instruction = instructions[index % len(instructions)]
    elif index < len(instructions):
        instruction = instructions[index]
    else:
        return None

    return apply_modifiers(
        voice.sound(instruction, performance.feature_values),
        performance.transpose,
        performance.volume,
    )
