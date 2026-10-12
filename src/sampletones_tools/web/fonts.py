from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Optional, Tuple

from sampletones_application.layout.fonts import Typeface
from sampletones_shared.paths.resources import (
    FONT_ICON,
    FONT_MONO_BOLD,
    FONT_MONO_REGULAR,
    FONT_SANS_BOLD,
    FONT_SANS_ITALIC,
    FONT_SANS_REGULAR,
)

SANS_FAMILY: Final[str] = "SampleToNES Sans"
MONO_FAMILY: Final[str] = "SampleToNES Mono"
ICON_FAMILY: Final[str] = "SampleToNES Glyphs"

REGULAR_WEIGHT: Final[int] = 400
BOLD_WEIGHT: Final[int] = 700
NORMAL_STYLE: Final[str] = "normal"
ITALIC_STYLE: Final[str] = "italic"

FONT_MEDIA_TYPE: Final[str] = "font/ttf"

FONT_STACKS: Final[Dict[Typeface, str]] = {
    Typeface.SANS: f'"{SANS_FAMILY}", "{ICON_FAMILY}", system-ui, sans-serif',
    Typeface.MONO: f'"{MONO_FAMILY}", "{ICON_FAMILY}", ui-monospace, monospace',
    Typeface.ICON: f'"{ICON_FAMILY}", sans-serif',
}


@dataclass(frozen=True)
class PageFont:
    """One face a page draws with, and the file it is read from."""

    family: str
    weight: int
    style: str
    filename: str


PAGE_FONTS: Final[Tuple[PageFont, ...]] = (
    PageFont(family=SANS_FAMILY, weight=REGULAR_WEIGHT, style=NORMAL_STYLE, filename=FONT_SANS_REGULAR),
    PageFont(family=SANS_FAMILY, weight=BOLD_WEIGHT, style=NORMAL_STYLE, filename=FONT_SANS_BOLD),
    PageFont(family=SANS_FAMILY, weight=REGULAR_WEIGHT, style=ITALIC_STYLE, filename=FONT_SANS_ITALIC),
    PageFont(family=MONO_FAMILY, weight=REGULAR_WEIGHT, style=NORMAL_STYLE, filename=FONT_MONO_REGULAR),
    PageFont(family=MONO_FAMILY, weight=BOLD_WEIGHT, style=NORMAL_STYLE, filename=FONT_MONO_BOLD),
)
ICON_FONT: Final[PageFont] = PageFont(
    family=ICON_FAMILY,
    weight=REGULAR_WEIGHT,
    style=NORMAL_STYLE,
    filename=FONT_ICON,
)


def fonts_stylesheet(
    directory: Path,
    glyph_characters: str,
) -> str:
    """The application's faces, embedded so a page draws with them wherever it is opened.

    A page opened from a file has an origin of its own, and browsers refuse a face read from a
    folder other than the page's, so each face travels inside the stylesheet. The glyph face
    answers only for the glyph characters, which keeps every other character in the text faces.

    Raises:
        FileNotFoundError: If ``directory`` holds no file of a face's name.
    """
    faces = [_face(font, directory, None) for font in PAGE_FONTS]
    faces.append(_face(ICON_FONT, directory, unicode_range(glyph_characters)))
    return "\n".join(faces) + "\n"


def unicode_range(characters: str) -> str:
    """The characters as a CSS ``unicode-range``, consecutive code points joined into spans."""
    codepoints = sorted({ord(character) for character in characters})
    spans: List[Tuple[int, int]] = []
    for codepoint in codepoints:
        if spans and codepoint == spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], codepoint)
        else:
            spans.append((codepoint, codepoint))

    return ", ".join(f"U+{start:04X}" if start == end else f"U+{start:04X}-{end:04X}" for start, end in spans)


def _face(
    font: PageFont,
    directory: Path,
    characters: Optional[str],
) -> str:
    encoded = b64encode((directory / font.filename).read_bytes()).decode("ascii")
    lines = [
        "@font-face {",
        f'  font-family: "{font.family}";',
        f"  font-weight: {font.weight};",
        f"  font-style: {font.style};",
        "  font-display: block;",
        f'  src: url("data:{FONT_MEDIA_TYPE};base64,{encoded}") format("truetype");',
    ]
    if characters is not None:
        lines.append(f"  unicode-range: {characters};")
    lines.append("}")
    return "\n".join(lines)
