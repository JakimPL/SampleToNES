from typing import Final

from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import relative_luminance

OPAQUE_ALPHA: Final[int] = 255
DARK_SCHEME: Final[str] = "dark"
LIGHT_SCHEME: Final[str] = "light"
LIGHT_GROUND_LUMINANCE: Final[float] = 0.5


def css_color(color: ColorRGBA) -> str:
    """A color as CSS writes it: six hexadecimal digits, eight where it is translucent."""
    red, green, blue, alpha = color
    opaque = f"#{red:02x}{green:02x}{blue:02x}"
    return opaque if alpha == OPAQUE_ALPHA else f"{opaque}{alpha:02x}"


def color_scheme(ground: ColorRGBA) -> str:
    """The CSS color scheme a page standing on ``ground`` asks for, so form controls and
    scrollbars match it: ``light`` on a light ground, ``dark`` otherwise."""
    return LIGHT_SCHEME if relative_luminance(ground) >= LIGHT_GROUND_LUMINANCE else DARK_SCHEME
