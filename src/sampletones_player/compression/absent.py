from sampletones_player.specification.compression import INITIAL_PLANE_VALUE


def is_absent(plane: bytes) -> bool:
    """Whether a plane plays only the value every plane starts at, so the block leaves it out.

    The driver starts every plane at that value and leaves an absent one standing there, which
    is what makes a channel that never bends cost its bend plane nothing.

    Args:
        plane: The values the plane plays.

    Returns:
        bool: Whether the plane holds no other value.
    """
    return set(plane) <= {INITIAL_PLANE_VALUE}
