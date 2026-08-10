from typing import Tuple


def nearest_offered(value: int, offered: Tuple[int, ...]) -> int:
    """The offered number a standing choice selects: the closest one, the smaller where two tie.

    A choice outlives the list that was offered when it was made — a frame rate a build has
    since dropped, a sample rate the newly chosen format encodes nothing near — so snapping it
    onto the offer keeps a combo showing a value that is in force.

    Args:
        value: The number a choice stands at.
        offered: The numbers on offer.

    Returns:
        int: The offered number the choice selects.

    Raises:
        ValueError: when nothing is offered.
    """
    if not offered:
        raise ValueError("Selecting a value requires at least one offered number")

    return min(offered, key=lambda candidate: (abs(candidate - value), candidate))
