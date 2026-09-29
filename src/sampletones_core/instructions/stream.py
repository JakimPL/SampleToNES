from typing import Iterable

from .instruction import Instruction


def sounds(stream: Iterable[Instruction]) -> bool:
    """Whether a channel's stream sounds in any of its frames.

    A channel whose every frame rests plays nothing, so this is what tells a channel in play from
    one standing by, whatever left it silent.

    Args:
        stream: The instructions a channel plays, one per frame.

    Returns:
        bool: True where some frame sounds.
    """
    return any(instruction.on for instruction in stream)
