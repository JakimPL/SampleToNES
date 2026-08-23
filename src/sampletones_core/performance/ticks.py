from typing import Optional

from sampletones_core.instructions import InstructionUnion
from sampletones_core.performance.modifiers import apply_modifiers
from sampletones_core.performance.state import ChannelPerformance
from sampletones_core.performance.voice import VoiceReading


def sound_tick(
    performance: ChannelPerformance,
    reading: VoiceReading,
) -> Optional[InstructionUnion]:
    """The instruction a channel sounds this tick, and the step onto the next one.

    The channel moves on a tick whatever the reading answers, so a voice that has run out keeps
    counting and a row starting a note lands it back at the beginning.

    Args:
        performance: What the channel carries; its tick index moves on.
        reading: How this channel reads the sounding voice.

    Returns:
        Optional[InstructionUnion]: The instruction to sound, or ``None`` where the voice has
            played out and the channel rests.
    """
    index = performance.tick_index
    performance.tick_index += 1

    instruction = reading.at(index)
    if instruction is None:
        return None

    return apply_modifiers(
        reading.sound(instruction, performance.feature_values),
        performance.transpose,
        performance.volume,
    )
