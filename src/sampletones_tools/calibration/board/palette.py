from typing import Final, Tuple

from sampletones_application.paths import PALETTES_DIRECTORY
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME, PaletteCatalog
from sampletones_application.utils.palette.palette import Palette
from sampletones_shared.types.application import ColorRGBA

DEFAULT_PALETTE: Final[str] = DEFAULT_PALETTE_NAME
OPAQUE_ALPHA: Final[int] = 255
CHANNEL_TOKEN_PREFIX: Final[str] = "channel_"


def board_palette(name: str) -> Palette:
    """The palette a page is drawn in, by the name the application knows it under.

    Raises:
        KeyError: If the build ships no palette of that name.
    """
    return PaletteCatalog.load(PALETTES_DIRECTORY).get(name)


def palette_names() -> Tuple[str, ...]:
    """Every palette name a page may be drawn in, the application's own default among them."""
    return PaletteCatalog.load(PALETTES_DIRECTORY).names


def palette_stylesheet(palette: Palette) -> str:
    """The palette's tokens as custom properties, under the names the application states them by.

    A token keeps its name from the palette file to the page, so a color the application draws with
    and the color the page draws with are one value read from one place.

    Args:
        palette: The palette the page is drawn in.

    Returns:
        The stylesheet, one ``:root`` block holding every token.
    """
    declarations = "".join(f"  --{token}: {css_color(color)};\n" for token, color in sorted(palette.colors.items()))
    return f":root {{\n{declarations}}}\n"


def channel_token(channel: str) -> str:
    """The palette token a channel's color stands under."""
    return f"{CHANNEL_TOKEN_PREFIX}{channel}"


def css_color(color: ColorRGBA) -> str:
    """A palette color as CSS writes it: six hexadecimal digits, eight where it is translucent."""
    red, green, blue, alpha = color
    opaque = f"#{red:02x}{green:02x}{blue:02x}"
    return opaque if alpha == OPAQUE_ALPHA else f"{opaque}{alpha:02x}"
