from typing import List


def _split_version(version: str) -> List[int]:
    """
    Splits a dotted version string into its integer components.

    Args:
        version (str): A dotted version string such as ``1.4.0``.

    Returns:
        List[int]: The version's numeric components in order.

    Raises:
        SystemError: If any component is not an integer.
    """
    try:
        return list(map(int, version.split(".")))
    except ValueError as exception:
        raise SystemError(f"Invalid version format: {exception}") from exception


def compare_versions(version1: str, version2: str) -> int:
    """
    Compares two dotted version strings numerically.

    Shorter versions are zero-padded, so ``1.2`` and ``1.2.0`` compare equal.

    Args:
        version1 (str): First dotted version string (e.g. ``1.4.0``).
        version2 (str): Second dotted version string.

    Returns:
        int: ``-1`` if version1 precedes version2, ``1`` if it follows, ``0`` if they are equal.

    Raises:
        SystemError: If either string holds a non-integer component.
    """
    v1_parts = _split_version(version1)
    v2_parts = _split_version(version2)

    length_difference = len(v1_parts) - len(v2_parts)
    if length_difference > 0:
        v2_parts.extend([0] * length_difference)

    elif length_difference < 0:
        v1_parts.extend([0] * -length_difference)

    for part1, part2 in zip(v1_parts, v2_parts):
        if part1 < part2:
            return -1

        if part1 > part2:
            return 1

    return 0
