from pathlib import Path

from sampletones_core.paths import EXT_FILE_LIBRARY
from sampletones_shared.types.path import Pathlike

from .key import InstructionLibraryKey


# TODO: change; relying on the filename is error-prone
def create_key_from_filename(filename: Pathlike) -> InstructionLibraryKey:
    filename = Path(filename).stem
    file_parts = filename.split("_")
    if len(file_parts) != 10:
        raise ValueError(f"Invalid library file name format: {filename}")

    sample_rate = int(file_parts[1])
    change_rate = int(file_parts[3])
    window_size = int(file_parts[5])
    transformation_gamma = int(file_parts[7])
    config_hash = file_parts[9]
    frame_length = round(sample_rate / change_rate)

    return InstructionLibraryKey(
        sample_rate=sample_rate,
        frame_length=frame_length,
        window_size=window_size,
        transformation_gamma=transformation_gamma,
        config_hash=config_hash,
        filename=f"{filename}{EXT_FILE_LIBRARY}",
    )


def get_display_name_from_key(key: InstructionLibraryKey) -> str:
    sample_rate = key.sample_rate
    change_rate = round(sample_rate / key.frame_length)
    transformation_gamma = key.transformation_gamma
    hash_part = key.config_hash[:7]
    return f"{sample_rate}_{change_rate}_{transformation_gamma}_{hash_part}"
