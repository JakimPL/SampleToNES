from typing import Sequence


def require_unique_names(names: Sequence[str], kind: str) -> None:
    """Holds every sound of a corpus to a name of its own, which its files and its readings go by.

    Raises:
        ValueError: If two of ``names`` are alike, naming the ``kind`` of sound in the message.
    """
    if len(set(names)) != len(names):
        raise ValueError(f"Every {kind} must have a name of its own")
