from typing import Annotated, Any, Final

import numpy as np
from pydantic import BeforeValidator

from sampletones_shared.constants.general import HEXADECIMAL_BASE
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.arrays import clamp

MAX_CHANNEL_VALUE: Final[int] = 255
RGB_CHANNELS: Final[int] = 3
SRGB_LINEAR_LIMIT: Final[float] = 0.03928
SRGB_LINEAR_SLOPE: Final[float] = 12.92
SRGB_OFFSET: Final[float] = 0.055
SRGB_GAMMA: Final[float] = 2.4
LUMINANCE_WEIGHTS: Final[np.ndarray] = np.array([0.2126, 0.7152, 0.0722])
CONTRAST_OFFSET: Final[float] = 0.05


def with_alpha_fraction(color: ColorRGBA, fraction: float) -> ColorRGBA:
    """Return ``color`` with its alpha set to ``fraction`` of full opacity.

    ``fraction`` is a value in ``[0, 1]``; ``1`` keeps the color fully opaque and
    ``0`` makes it fully transparent, letting callers express a tint strength as a
    fraction while colors stay 8-bit RGBA tuples.
    """
    red, green, blue, _ = color
    return (red, green, blue, round(fraction * MAX_CHANNEL_VALUE))


def blend(start: ColorRGBA, end: ColorRGBA, fraction: float) -> ColorRGBA:
    """Linearly interpolate between two colors, channel by channel.

    ``fraction`` is clamped to ``[0, 1]``: ``0`` returns ``start`` and ``1`` returns ``end``, with
    every RGBA channel mixed in proportion so a scalar can drive a color along a gradient.
    """
    ratio = clamp(fraction, 0.0, 1.0)
    start_channels = np.array(start, dtype=np.float64)
    end_channels = np.array(end, dtype=np.float64)
    channels = np.rint(start_channels + (end_channels - start_channels) * ratio).astype(int)
    return (int(channels[0]), int(channels[1]), int(channels[2]), int(channels[3]))


def composite(base: ColorRGBA, overlay: ColorRGBA) -> ColorRGBA:
    """Return the color ``overlay`` makes when it is drawn over ``base``.

    Each color carries its own alpha, and the result carries the coverage the two reach
    together, so a pair of translucent washes bound for a single layer reads as it would if
    the layer held both. A fully transparent pair returns ``base``.
    """
    base_channels = np.array(base, dtype=np.float64) / MAX_CHANNEL_VALUE
    overlay_channels = np.array(overlay, dtype=np.float64) / MAX_CHANNEL_VALUE
    base_alpha = base_channels[3] * (1.0 - overlay_channels[3])
    alpha = overlay_channels[3] + base_alpha
    if alpha == 0.0:
        return base

    colors = (overlay_channels[:3] * overlay_channels[3] + base_channels[:3] * base_alpha) / alpha
    channels = np.rint(np.append(colors, alpha) * MAX_CHANNEL_VALUE).astype(int)
    return (int(channels[0]), int(channels[1]), int(channels[2]), int(channels[3]))


def relative_luminance(color: ColorRGBA) -> float:
    """Return how bright ``color`` reads, from ``0.0`` for black to ``1.0`` for white, as the WCAG defines it.

    Each channel is linearized out of the sRGB curve before the channels are weighted, so two
    colors with the same figure read equally bright whatever their hue. The alpha is left out:
    the figure describes the color as drawn.
    """
    channels = np.array(color[:RGB_CHANNELS], dtype=np.float64) / MAX_CHANNEL_VALUE
    linear = np.where(
        channels <= SRGB_LINEAR_LIMIT,
        channels / SRGB_LINEAR_SLOPE,
        ((channels + SRGB_OFFSET) / (1.0 + SRGB_OFFSET)) ** SRGB_GAMMA,
    )
    return float(np.dot(LUMINANCE_WEIGHTS, linear))


def contrast_ratio(first: ColorRGBA, second: ColorRGBA) -> float:
    """Return the WCAG contrast between two colors as drawn, from ``1.0`` for alike to ``21.0`` for black on white.

    The ratio reads the same whichever color is the text and whichever the background, so a
    floor a palette is held to can be stated once for every pairing.
    """
    first_luminance = relative_luminance(first)
    second_luminance = relative_luminance(second)
    lighter = max(first_luminance, second_luminance)
    darker = min(first_luminance, second_luminance)
    return (lighter + CONTRAST_OFFSET) / (darker + CONTRAST_OFFSET)


def to_grayscale(color: ColorRGBA) -> ColorRGBA:
    """Return ``color`` desaturated to its luminance-preserving gray, keeping its alpha.

    The RGB channels collapse to one perceptual-luminance value, so a colored line reads
    as an inactive gray while its alpha stays under the caller's separate control.
    """
    red, green, blue, alpha = color
    luminance = round(0.299 * red + 0.587 * green + 0.114 * blue)
    return (luminance, luminance, luminance, alpha)


def parse_hex_color(value: str) -> ColorRGBA:
    """Parse a hex color string to an RGBA tuple.

    Accepts ``#rrggbb`` (opaque, alpha defaults to 255) or ``#rrggbbaa``
    (with explicit alpha).  Leading and trailing whitespace is stripped before
    validation.

    Validation rules:
    - First character after stripping must be ``#``.
    - The remaining characters must be exactly 6 or 8 hexadecimal digits
      (i.e. at most 8, with a minimum of 6 to form a valid RGB triplet).

    Raises:
        ValueError: if any validation rule is violated.
    """
    stripped = value.strip()
    if not stripped.startswith("#"):
        raise ValueError(f"Color must start with '#', got: {value!r}")

    hex_part = stripped[1:]
    if len(hex_part) not in (6, 8):
        raise ValueError(f"Color must have 6 or 8 hex digits after '#', got {len(hex_part)}: {value!r}")

    try:
        int(hex_part, HEXADECIMAL_BASE)
    except ValueError as exception:
        raise ValueError(f"Color contains non-hex characters: {value!r}") from exception

    r = int(hex_part[0:2], HEXADECIMAL_BASE)
    g = int(hex_part[2:4], HEXADECIMAL_BASE)
    b = int(hex_part[4:6], HEXADECIMAL_BASE)
    a = int(hex_part[6:8], HEXADECIMAL_BASE) if len(hex_part) == 8 else 255

    return (r, g, b, a)


def _rgba_validator(value: Any) -> ColorRGBA:
    if isinstance(value, str):
        return parse_hex_color(value)

    raise ValueError(f"Expected a hex color string (e.g. '#rrggbb'), got {type(value).__name__}: {value!r}")


RGBA = Annotated[ColorRGBA, BeforeValidator(_rgba_validator)]
