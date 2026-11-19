from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from sampletones_core.configs.display import (
    DISPLAY_SEPARATOR,
    format_frequencies,
    format_transformation,
)
from sampletones_core.library.filename.fields import InstructionsFilenameFields
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_shared.types.path import Pathlike


def library_key_from_filename(filename: Pathlike) -> Optional[InstructionLibraryKey]:
    """The key a library file's name states, or ``None`` where the name is not one a library is
    written under or states settings out of a library's range.

    A library folder may hold any file, so the listing probes every name here and lists the ones
    that answer.
    """
    fields = InstructionsFilenameFields.parse(filename)
    if fields is None:
        return None

    try:
        return InstructionLibraryKey(
            sample_rate=fields.sr,
            nes_frequency=fields.nf,
            frame_length=round(fields.sr / fields.nf),
            window_size=fields.ws,
            transformation_gamma=fields.tg,
            spectrum_method=fields.sm,
            config_hash=fields.ch,
            filename=fields.filename,
        )
    except ValidationError:
        return None


def create_key_from_filename(filename: Pathlike) -> InstructionLibraryKey:
    """The key a library file's name states.

    Raises:
        ValueError: If the name is not one a library is written under.
    """
    key = library_key_from_filename(filename)
    if key is None:
        raise ValueError(f"Not a library file name: {Path(filename).name}")

    return key


def get_display_name_from_key(key: InstructionLibraryKey) -> str:
    return DISPLAY_SEPARATOR.join(
        [
            format_frequencies(key.sample_rate, key.nes_frequency),
            format_transformation(key.spectrum_method, key.transformation_gamma),
        ]
    )
