from sampletones_player.specification.compression import INITIAL_PLANE_VALUE


def is_absent(played: bytes) -> bool:
    """Whether a plane a study prices holds the value a plane starts at throughout.

    A study weighs layouts whose planes answer to no plane of the song block, so it reads
    absence off the values alone rather than off the plane the block would write.

    Args:
        played: The values the plane plays.

    Returns:
        bool: Whether the plane holds that value and no other.
    """
    return set(played) <= {INITIAL_PLANE_VALUE}
