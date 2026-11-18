from typing import Final, List, Tuple

from sampletones_player.specification.screen import TILE_SIDE
from sampletones_tools.player.graphics.deck.state import MAX_LEVEL

PROGRESS_STEPS: Final[int] = TILE_SIDE
METER_STEPS_PER_TILE: Final[int] = 2
METER_PAIRS: Final[int] = MAX_LEVEL // METER_STEPS_PER_TILE


def meter_members(level: int) -> Tuple[str, ...]:
    """The tiles a level meter shows for a volume, left to right.

    A tile holds two steps of the meter, and the last tile holds the fifteenth step alone.

    Args:
        level: The volume, from zero to fifteen.

    Returns:
        Tuple[str, ...]: The member each of the meter's tiles shows.
    """
    pairs: List[str] = []
    for pair in range(METER_PAIRS):
        lit = min(max(level - pair * METER_STEPS_PER_TILE, 0), METER_STEPS_PER_TILE)
        pairs.append(("meter_none", "meter_first", "meter_both")[lit])

    return (*pairs, "meter_last_lit" if level >= MAX_LEVEL else "meter_last_dim")


def progress_members(filled: int, width: int) -> Tuple[str, ...]:
    """The tiles a progress bar shows with ``filled`` of its pixels reached.

    Args:
        filled: The pixels filled, counted from the bar's left end.
        width: The cells the bar spans.

    Returns:
        Tuple[str, ...]: The member each of the bar's tiles shows.
    """
    return tuple(f"progress_{min(max(filled - cell * PROGRESS_STEPS, 0), PROGRESS_STEPS)}" for cell in range(width))
