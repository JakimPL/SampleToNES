import shutil
from pathlib import Path
from typing import Final

import numpy as np
from PIL import Image

FRAME_PATTERN: Final[str] = "%06d.png"
FRAME_FORMAT: Final[str] = "PNG"
COMPRESSION_LEVEL: Final[int] = 1
PARTIAL_SUFFIX: Final[str] = ".partial"
SHOOT_FILE: Final[str] = "shoot.json"


def frame_path(folder: Path, index: int) -> Path:
    """Where frame ``index`` of the footage is kept in ``folder``."""
    return folder / (FRAME_PATTERN % index)


def filmed(folder: Path) -> int:
    """How many frames stand filmed in ``folder``, counted from the first up to the first one missing."""
    count = 0
    while frame_path(folder, count).is_file():
        count += 1

    return count


def write_frame(frame: np.ndarray, target: Path) -> None:
    """Writes ``frame``, rows of eight-bit red, green and blue levels, to ``target`` whole, so a run cut short
    leaves every frame it kept readable.
    """
    partial = target.with_name(target.name + PARTIAL_SUFFIX)
    Image.fromarray(frame).save(partial, FRAME_FORMAT, compress_level=COMPRESSION_LEVEL)
    partial.replace(target)


def prepare_frames(folder: Path, shoot: str, *, fresh: bool) -> None:
    """Keeps the frames in ``folder`` filmed for ``shoot``, empties it for a shoot of its own or where ``fresh``
    asks for it, and records ``shoot`` there.
    """
    record = folder / SHOOT_FILE
    if folder.exists() and (fresh or not record.is_file() or record.read_text() != shoot):
        shutil.rmtree(folder)

    folder.mkdir(parents=True, exist_ok=True)
    record.write_text(shoot)
