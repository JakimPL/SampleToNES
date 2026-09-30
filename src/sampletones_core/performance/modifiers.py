from typing import Final

from sampletones_core.constants.general import MAX_VOLUME, MIN_VOLUME, SILENT_VOLUME
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.utils.frequencies import transpose_period, transpose_pitch

TRIANGLE_LOUDEST_SILENT_VOLUME: Final[int] = MAX_VOLUME // 2


def triangle_sounds_at(row_volume: int) -> bool:
    """Whether the triangle sounds at the level a pattern has reached.

    The triangle plays at one fixed loudness, so a pattern's level decides only whether it sounds,
    and it sounds while the row asks for more than half volume. A tracker export writes the
    triangle's volume column by this rule, so the tracker gates the triangle where the song does.

    Args:
        row_volume: The level the pattern has reached.

    Returns:
        bool: Whether the triangle sounds at that level.
    """
    return row_volume > TRIANGLE_LOUDEST_SILENT_VOLUME


def pulse_volume(
    volume: int,
    row_volume: int,
) -> int:
    """The level a pulse channel sounds at: the instruction's level scaled by the row's, to the nearest step.

    Args:
        volume: The level the instruction holds.
        row_volume: The level the pattern has reached.

    Returns:
        int: The level the channel sounds at.
    """
    return max(SILENT_VOLUME, min(MAX_VOLUME, round(volume * row_volume / MAX_VOLUME)))


def noise_volume(
    volume: int,
    row_volume: int,
) -> int:
    """The level the noise channel sounds at: the instruction's level scaled by the row's, rounded down.

    A product that rounds down to silence while both levels sound is raised to the quietest level, so a
    quiet row keeps the noise audible. FamiTracker and Bitphase both set the noise level by this rule,
    so an exported song's noise plays there at the level it plays here.

    Args:
        volume: The level the instruction holds.
        row_volume: The level the pattern has reached.

    Returns:
        int: The level the channel sounds at.
    """
    scaled = max(SILENT_VOLUME, min(MAX_VOLUME, volume * row_volume // MAX_VOLUME))
    if scaled == SILENT_VOLUME and volume > SILENT_VOLUME and row_volume > SILENT_VOLUME:
        return MIN_VOLUME

    return scaled


def apply_modifiers(
    instruction: InstructionUnion,
    transpose: int,
    row_volume: int,
) -> InstructionUnion:
    """Bends one tick's instruction by the transpose and volume the pattern has reached.

    A sample carries the instructions it was reconstructed from; a pattern states how loud and how
    high it is played. Each channel takes both in the terms it understands: the pulse channels
    scale their volume by :func:`pulse_volume` and shift their pitch, the triangle shifts its pitch
    and sounds while the row asks for more than half volume, and the noise channel scales its
    volume by :func:`noise_volume` and walks its period around the sixteen the hardware offers.

    Args:
        instruction: The tick's instruction as the sample holds it.
        transpose: The semitone offset the pattern has reached, held within the pitch range.
        row_volume: The level the pattern has reached, scaling the instruction's own.

    Returns:
        InstructionUnion: A copy of the instruction as the channel sounds it.
    """
    match instruction:
        case PulseInstruction():
            scaled_volume = pulse_volume(instruction.volume, row_volume)
            effective_pitch = transpose_pitch(instruction.pitch, transpose)
            return instruction.model_copy(update={"pitch": effective_pitch, "volume": scaled_volume})
        case TriangleInstruction():
            effective_pitch = transpose_pitch(instruction.pitch, transpose)
            on = instruction.on and triangle_sounds_at(row_volume)
            return instruction.model_copy(update={"pitch": effective_pitch, "on": on})
        case NoiseInstruction():
            scaled_volume = noise_volume(instruction.volume, row_volume)
            effective_period = transpose_period(instruction.period, transpose)
            return instruction.model_copy(update={"period": effective_period, "volume": scaled_volume})
