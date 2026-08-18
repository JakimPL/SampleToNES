from pathlib import Path
from typing import List, Tuple

from PIL import Image

from sampletones_assets.mark.raster import MarkRaster
from sampletones_assets.mark.specification import Mark
from sampletones_assets.mark.vector import render_vector
from sampletones_shared.paths.resources import (
    ICON_UNIX_FILENAME,
    ICON_VECTOR_FILENAME,
    ICON_WIN_FILENAME,
)


def _resized(master: Image.Image, size: int) -> Image.Image:
    return master.resize((size, size), Image.Resampling.LANCZOS)


def _write_vector(path: Path, mark: Mark) -> Path:
    path.write_text(render_vector(mark), encoding="utf-8")
    return path


def _write_raster(path: Path, master: Image.Image, size: int) -> Path:
    _resized(master, size).save(path)
    return path


def _write_windows_icon(
    path: Path,
    master: Image.Image,
    sizes: Tuple[int, ...],
) -> Path:
    """Writes the multi-resolution icon, rendering one frame per declared size.

    Every frame is resampled from the supersampled master, so a 16 px frame carries the
    detail the design grid puts there.
    """
    primary, *appended = (_resized(master, size) for size in sizes)
    primary.save(
        path,
        format="ICO",
        sizes=[(size, size) for size in sizes],
        append_images=appended,
    )
    return path


def write_icon_suite(directory: Path, mark: Mark) -> List[Path]:
    """Writes the vector, the raster and the Windows icon the application ships.

    Args:
        directory (Path): Directory receiving the icon files, created where it is missing.
        mark (Mark): Design definition every file is drawn from.

    Returns:
        List[Path]: The files written, in the order they were produced.
    """
    directory.mkdir(parents=True, exist_ok=True)
    master = MarkRaster(mark).render()

    return [
        _write_vector(directory / ICON_VECTOR_FILENAME, mark),
        _write_raster(directory / ICON_UNIX_FILENAME, master, mark.render.raster_size),
        _write_windows_icon(directory / ICON_WIN_FILENAME, master, mark.render.windows_sizes),
    ]
