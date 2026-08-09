from typing import Annotated, Any, Final

import numpy as np
from pydantic import BeforeValidator

from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.arrays import clamp

MAX_CHANNEL_VALUE: Final[int] = 255


def with_alpha_fraction(color: ColorRGBA, fraction: float) -> ColorRGBA:
    """Return ``color`` with its alpha set to ``fraction`` of full opacity.

    ``fraction`` is a value in ``[0, 1]``; ``1`` keeps the colour fully opaque and
    ``0`` makes it fully transparent, letting callers express a tint strength as a
    fraction while colours stay 8-bit RGBA tuples.
    """
    red, green, blue, _ = color
    return (red, green, blue, round(fraction * MAX_CHANNEL_VALUE))


def blend(start: ColorRGBA, end: ColorRGBA, fraction: float) -> ColorRGBA:
    """Linearly interpolate between two colours, channel by channel.

    ``fraction`` is clamped to ``[0, 1]``: ``0`` returns ``start`` and ``1`` returns ``end``, with
    every RGBA channel mixed in proportion so a scalar can drive a colour along a gradient.
    """
    ratio = clamp(fraction, 0.0, 1.0)
    start_channels = np.array(start, dtype=np.float64)
    end_channels = np.array(end, dtype=np.float64)
    channels = np.rint(start_channels + (end_channels - start_channels) * ratio).astype(int)
    return (int(channels[0]), int(channels[1]), int(channels[2]), int(channels[3]))


def composite(base: ColorRGBA, overlay: ColorRGBA) -> ColorRGBA:
    """Return the colour ``overlay`` makes when it is drawn over ``base``.

    Each colour carries its own alpha, and the result carries the coverage the two reach
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


def to_grayscale(color: ColorRGBA) -> ColorRGBA:
    """Return ``color`` desaturated to its luminance-preserving gray, keeping its alpha.

    The RGB channels collapse to one perceptual-luminance value, so a coloured line reads
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
        int(hex_part, 16)
    except ValueError as exception:
        raise ValueError(f"Color contains non-hex characters: {value!r}") from exception

    r = int(hex_part[0:2], 16)
    g = int(hex_part[2:4], 16)
    b = int(hex_part[4:6], 16)
    a = int(hex_part[6:8], 16) if len(hex_part) == 8 else 255

    return (r, g, b, a)


def _rgba_validator(value: Any) -> ColorRGBA:
    if isinstance(value, str):
        return parse_hex_color(value)

    raise ValueError(f"Expected a hex color string (e.g. '#rrggbb'), got {type(value).__name__}: {value!r}")


RGBA = Annotated[ColorRGBA, BeforeValidator(_rgba_validator)]
