from pathlib import Path

from sampletones_core.configs.display import (
    DISPLAY_SEPARATOR,
    format_frequencies,
    format_transformation,
)
from sampletones_core.library.filename.fields import InstructionsFilenameFields
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_shared.paths.extensions import EXT_FILE_LIBRARY
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import get_filename


def create_key_from_filename(filename: Pathlike) -> InstructionLibraryKey:
    filename = Path(filename).stem
    fields = InstructionsFilenameFields.create(filename)

    sample_rate = fields.sr
    nes_frequency = fields.nf
    window_size = fields.ws
    transformation_gamma = fields.tg
    spectrum_method = fields.sm
    config_hash = fields.ch
    frame_length = round(sample_rate / nes_frequency)

    return InstructionLibraryKey(
        sample_rate=sample_rate,
        frame_length=frame_length,
        window_size=window_size,
        transformation_gamma=transformation_gamma,
        spectrum_method=spectrum_method,
        config_hash=config_hash,
        filename=get_filename(filename, EXT_FILE_LIBRARY),
    )


def get_display_name_from_key(key: InstructionLibraryKey) -> str:
    nes_frequency = round(key.sample_rate / key.frame_length)
    return DISPLAY_SEPARATOR.join(
        [
            format_frequencies(key.sample_rate, nes_frequency),
            format_transformation(key.spectrum_method, key.transformation_gamma),
        ]
    )
