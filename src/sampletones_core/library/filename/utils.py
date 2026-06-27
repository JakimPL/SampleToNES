from pathlib import Path

from sampletones_core.configs.display import (
    DISPLAY_SEPARATOR,
    GAMMA_PREFIX,
    format_nes_frequency,
    format_sample_rate,
)
from sampletones_core.library.filename.fields import InstructionsFilenameFields
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_core.paths import EXT_FILE_LIBRARY
from sampletones_shared.types.path import Pathlike


def create_key_from_filename(filename: Pathlike) -> InstructionLibraryKey:
    filename = Path(filename).stem
    fields = InstructionsFilenameFields.create(filename)

    sample_rate = fields.sr
    nes_frequency = fields.nf
    window_size = fields.ws
    transformation_gamma = fields.tg
    config_hash = fields.ch
    frame_length = round(sample_rate / nes_frequency)

    return InstructionLibraryKey(
        sample_rate=sample_rate,
        frame_length=frame_length,
        window_size=window_size,
        transformation_gamma=transformation_gamma,
        config_hash=config_hash,
        filename=f"{filename}{EXT_FILE_LIBRARY}",
    )


def get_display_name_from_key(key: InstructionLibraryKey) -> str:
    nes_frequency = round(key.sample_rate / key.frame_length)
    gamma = f"{GAMMA_PREFIX}{key.transformation_gamma}"
    return DISPLAY_SEPARATOR.join(
        [
            format_sample_rate(key.sample_rate),
            format_nes_frequency(nes_frequency),
            gamma,
        ]
    )
