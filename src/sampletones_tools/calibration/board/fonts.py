from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Tuple

from sampletones_shared.paths.resources import (
    FONT_MONO_REGULAR,
    FONT_SANS_BOLD,
    FONT_SANS_REGULAR,
)

from .paths import FONTS_DIRECTORY

SANS_FAMILY: Final[str] = "SampleToNES Sans"
MONO_FAMILY: Final[str] = "SampleToNES Mono"

REGULAR_WEIGHT: Final[int] = 400
BOLD_WEIGHT: Final[int] = 600

FONT_MEDIA_TYPE: Final[str] = "font/ttf"


@dataclass(frozen=True)
class PageFont:
    """One face the page draws with, and the file it is read from.

    Attributes:
        family: The family name the stylesheet asks for.
        weight: The weight the face answers at.
        filename: The face's file in the assets package.
    """

    family: str
    weight: int
    filename: str


PAGE_FONTS: Final[Tuple[PageFont, ...]] = (
    PageFont(family=SANS_FAMILY, weight=REGULAR_WEIGHT, filename=FONT_SANS_REGULAR),
    PageFont(family=SANS_FAMILY, weight=BOLD_WEIGHT, filename=FONT_SANS_BOLD),
    PageFont(family=MONO_FAMILY, weight=REGULAR_WEIGHT, filename=FONT_MONO_REGULAR),
)


def fonts_stylesheet(directory: Path = FONTS_DIRECTORY) -> str:
    """The faces of the application, embedded so the page draws with them wherever it is opened.

    A page opened from a file has an origin of its own, and a face carried inside the stylesheet
    reaches it there as surely as it does over the web.

    Args:
        directory: The directory the face files are read from.

    Returns:
        The stylesheet, one ``@font-face`` rule per face.

    Raises:
        FileNotFoundError: If the directory holds no file of a face's name.
    """
    return "\n".join(_face(font, directory) for font in PAGE_FONTS) + "\n"


def _face(font: PageFont, directory: Path) -> str:
    encoded = b64encode((directory / font.filename).read_bytes()).decode("ascii")
    return (
        "@font-face {\n"
        f'  font-family: "{font.family}";\n'
        f"  font-weight: {font.weight};\n"
        "  font-style: normal;\n"
        "  font-display: block;\n"
        f'  src: url("data:{FONT_MEDIA_TYPE};base64,{encoded}") format("truetype");\n'
        "}"
    )
