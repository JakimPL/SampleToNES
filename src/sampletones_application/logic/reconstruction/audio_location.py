from pathlib import Path
from typing import Optional

from sampletones_core.reconstructions import Reconstruction


def resolve_original_audio(filepath: Path) -> Optional[Path]:
    """Reads a browsed reconstruction to recover the original audio location it records."""
    reconstruction = Reconstruction.load(filepath)
    return reconstruction.audio_filepath
