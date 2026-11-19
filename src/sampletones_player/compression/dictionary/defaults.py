from collections import Counter
from typing import Iterable, List, Tuple

from sampletones_player.specification.compression import NO_DEFAULT_COUNT


def modal_counts(plays: Iterable[Tuple[int, int]], phrases: int) -> Tuple[int, ...]:
    """The count each phrase is played at most often, the shortest breaking a tie.

    A phrase's default count is the one its tokens would leave unstated most often, so it is read
    off the plays a parse makes. A phrase no token plays keeps ``NO_DEFAULT_COUNT``.

    Args:
        plays: The phrase id and the tick count of every phrase a parse plays.
        phrases: The phrases the table holds.

    Returns:
        Tuple[int, ...]: The default count of each phrase, by id.
    """
    played: List[Counter[int]] = [Counter() for _ in range(phrases)]
    for phrase_id, ticks in plays:
        played[phrase_id][ticks] += 1

    return tuple(_modal(counter) for counter in played)


def _modal(played: Counter[int]) -> int:
    if not played:
        return NO_DEFAULT_COUNT

    return min(played, key=lambda ticks: (-played[ticks], ticks))
