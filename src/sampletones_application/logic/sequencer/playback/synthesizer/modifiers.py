from sampletones_core.constants.general import MAX_PITCH, MAX_VOLUME, MIN_PITCH
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)


def apply_modifiers(
    instruction: InstructionUnion,
    transpose: int,
    row_volume: int,
) -> InstructionUnion:
    """Bends one tick's instruction by the transpose and volume the pattern has reached.

    A sample carries the instructions it was reconstructed from; a pattern states how loud and how
    high it is played. Each channel takes both in the terms it understands: the pulse channels
    scale their volume and shift their pitch, the triangle shifts its pitch and sounds while the
    row asks for more than half volume, and the noise channel scales its volume and walks its
    period around the sixteen the hardware offers.

    Args:
        instruction: The tick's instruction as the sample holds it.
        transpose: The semitone offset the pattern has reached, held within the pitch range.
        row_volume: The level the pattern has reached, scaling the instruction's own.

    Returns:
        InstructionUnion: A copy of the instruction as the channel sounds it.
    """
    match instruction:
        case PulseInstruction():
            scaled_volume = max(0, min(MAX_VOLUME, round(instruction.volume * row_volume / MAX_VOLUME)))
            effective_pitch = max(MIN_PITCH, min(MAX_PITCH, instruction.pitch + transpose))
            return instruction.model_copy(update={"pitch": effective_pitch, "volume": scaled_volume})
        case TriangleInstruction():
            effective_pitch = max(MIN_PITCH, min(MAX_PITCH, instruction.pitch + transpose))
            on = instruction.on and row_volume > MAX_VOLUME // 2
            return instruction.model_copy(update={"pitch": effective_pitch, "on": on})
        case NoiseInstruction():
            scaled_volume = max(0, min(MAX_VOLUME, round(instruction.volume * row_volume / MAX_VOLUME)))
            effective_period = (instruction.period + transpose) % 16
            return instruction.model_copy(update={"period": effective_period, "volume": scaled_volume})
