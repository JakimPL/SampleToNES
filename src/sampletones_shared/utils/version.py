def compare_versions(version1: str, version2: str) -> int:
    v1_parts = list(map(int, version1.split(".")))
    v2_parts = list(map(int, version2.split(".")))

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
