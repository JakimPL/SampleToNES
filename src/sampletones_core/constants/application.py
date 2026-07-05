from typing import Final

SAMPLETONES_NAME: Final[str] = "SampleToNES"
SAMPLETONES_VERSION: Final[str] = "0.2.4"
SAMPLETONES_NAME_VERSION: Final[str] = f"{SAMPLETONES_NAME} v{SAMPLETONES_VERSION}"
SAMPLETONES_LIBRARY_DATA_VERSION: Final[str] = "1.1"
SAMPLETONES_RECONSTRUCTION_DATA_VERSION: Final[str] = "1.1"
SAMPLETONES_AUTHOR: Final[str] = "Jakim"
SAMPLETONES_GROUP: Final[str] = "Stage Magician"
SAMPLETONES_PACKAGE_NAME: Final[str] = "sampletones"


def compare_versions(version1: str, version2: str) -> int:
    v1_parts = [int(part) for part in version1.split(".")]
    v2_parts = [int(part) for part in version2.split(".")]

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
