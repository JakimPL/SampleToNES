from typing import Annotated

from pydantic import BeforeValidator


def parse_hex_color(value: str) -> tuple[int, int, int, int]:
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
    except ValueError as exc:
        raise ValueError(f"Color contains non-hex characters: {value!r}") from exc

    r = int(hex_part[0:2], 16)
    g = int(hex_part[2:4], 16)
    b = int(hex_part[4:6], 16)
    a = int(hex_part[6:8], 16) if len(hex_part) == 8 else 255

    return (r, g, b, a)


def _rgba_validator(value: object) -> tuple[int, int, int, int]:
    if isinstance(value, str):
        return parse_hex_color(value)
    raise ValueError(f"Expected a hex color string (e.g. '#rrggbb'), got {type(value).__name__}: {value!r}")


# Pydantic-compatible RGBA field type.  Accepts '#rrggbb' / '#rrggbbaa' strings
# and stores them as (r, g, b, a) integer tuples.
RGBA = Annotated[tuple[int, int, int, int], BeforeValidator(_rgba_validator)]
