from sampletones_core.instructions import (
    InstructionUnion,
    PulseInstruction,
    TriangleInstruction,
)

NO_BEND: int = 0


def playable(instruction: InstructionUnion) -> InstructionUnion:
    """One frame as the driver sounds it, which is at the note it names.

    A channel's plane states a pitch as its distance above the lowest note the song reaches, and
    that is what lets a phrase be transposed by adding to it — a divider offset added to an index
    means nothing there. A frame carrying a bend therefore sounds at its note's own divider until
    the planes gain a place to put one; ``docs/development/bugs-and-todos.md`` under **Tracker**
    owns that work.

    Stating it here is what makes the loss deliberate and single-placed: the encoders below read
    frames that carry no bend, and whoever holds the console's output against a reconstruction
    reads the same answer.

    Args:
        instruction: The frame as the reconstruction holds it.

    Returns:
        InstructionUnion: The frame the driver can sound.
    """
    match instruction:
        case PulseInstruction() | TriangleInstruction():
            if not instruction.bent:
                return instruction

            return instruction.model_copy(update={"detune": NO_BEND, "coarse_detune": NO_BEND})
        case _:
            return instruction
