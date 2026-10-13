from pathlib import Path
from typing import Dict, Final

from sampletones_application.layout.fonts import FontsLayout, Step, Typeface
from sampletones_shared.paths.resources import FONT_ICON, FONT_MONO_REGULAR, FONT_SANS_REGULAR
from sampletones_tools.web.typography.metrics import FontMetrics

SIZE_PRECISION: Final[int] = 2
TYPEFACE_FILES: Final[Dict[Typeface, str]] = {
    Typeface.SANS: FONT_SANS_REGULAR,
    Typeface.MONO: FONT_MONO_REGULAR,
    Typeface.ICON: FONT_ICON,
}


def size_name(typeface: Typeface, step: Step) -> str:
    """The name a page knows a size by, such as ``sans-medium``."""
    return f"{typeface.value}-{step.value}"


def type_sizes(
    fonts: FontsLayout,
    directory: Path,
) -> Dict[str, float]:
    """Every size the application draws text at, in CSS pixels, keyed by :func:`size_name`.

    Each typeface's sizes are converted with the metrics of its regular face, so a page at device
    scale 1 sets text exactly as large as the application draws it.

    Raises:
        FileNotFoundError: If ``directory`` lacks a typeface's regular face.
    """
    sizes: Dict[str, float] = {}
    for typeface in Typeface:
        factor = FontMetrics.read(directory / TYPEFACE_FILES[typeface]).em_per_pixel_height * fonts.scale
        for step in Step:
            sizes[size_name(typeface, step)] = round(fonts.size_for(typeface, step) * factor, SIZE_PRECISION)

    return sizes
