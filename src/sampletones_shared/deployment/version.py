from typing import List


def _split_version(version: str) -> List[int]:
    try:
        return list(map(int, version.split(".")))
    except ValueError as exception:
        raise SystemError(f"Invalid version format: {exception}") from exception


def compare_versions(version1: str, version2: str) -> int:
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
