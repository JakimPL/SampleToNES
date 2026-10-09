from typing import Final, List, Optional

from sampletones_core.features.envelope import Envelope
from sampletones_shared.constants.symbols import PIPE

LOOP_POINT: Final[str] = PIPE
ITEM_SEPARATOR: Final[str] = " "


def format_envelope(envelope: Envelope[int]) -> str:
    """Writes a dimension out as a reader types it: its values, spaced, around the point they repeat from.

    Args:
        envelope: The dimension to write out.

    Returns:
        str: The values separated by spaces, with ``|`` standing before the item they repeat from.
    """
    tokens: List[str] = [str(item) for item in envelope.items]
    if envelope.loop_point is not None:
        tokens.insert(envelope.loop_point, LOOP_POINT)

    return ITEM_SEPARATOR.join(tokens)


def parse_envelope(text: str) -> Envelope[int]:
    """Reads a dimension a reader typed, taking ``|`` as the item the values repeat from.

    Args:
        text: Whole numbers separated by spaces, with at most one ``|`` standing among them.

    Returns:
        Envelope[int]: The values written, repeating from the item ``|`` stands before.

    Raises:
        ValueError: Where a token is neither a whole number nor ``|``, where a second ``|`` stands
            among the values, or where ``|`` stands past the last value written.
    """
    items: List[int] = []
    loop_point: Optional[int] = None
    for token in text.split():
        if token != LOOP_POINT:
            items.append(int(token))
        elif loop_point is None:
            loop_point = len(items)
        else:
            raise ValueError(f"a dimension repeats from one item, and {text!r} marks two")

    return Envelope[int](items=tuple(items), loop_point=loop_point)
