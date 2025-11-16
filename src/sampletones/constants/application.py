from typing import Dict

SAMPLETONES_NAME = "SampleToNES"
SAMPLETONES_VERSION = "0.2.1"
SAMPLETONES_NAME_VERSION = f"{SAMPLETONES_NAME} v{SAMPLETONES_VERSION}"
SAMPLETONES_LIBRARY_DATA_VERSION = "1.0"
SAMPLETONES_RECONSTRUCTION_DATA_VERSION = "1.0"

SAMPLETONES_AUTHOR = "Jakim"
SAMPLETONES_GROUP = "Stage Magician"


def default_metadata(
    include_library_version: bool = True,
    include_reconstruction_version: bool = True,
) -> Dict[str, Dict[str, str]]:
    metadata = {"version": SAMPLETONES_VERSION}
    if include_library_version:
        metadata["library_data_version"] = SAMPLETONES_LIBRARY_DATA_VERSION
    if include_reconstruction_version:
        metadata["reconstruction_data_version"] = SAMPLETONES_RECONSTRUCTION_DATA_VERSION

    return {SAMPLETONES_NAME: metadata}


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
        elif part1 > part2:
            return 1

    return 0
