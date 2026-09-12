import re
from typing import Final

from sampletones_shared.utils.hashing import identity_digest

TAG_SEPARATOR: Final[str] = "."
TAG_DIGEST_LENGTH: Final[int] = 8

_WHITESPACE: Final[re.Pattern[str]] = re.compile(r"\s+")


def _normalize_segment(part: str) -> str:
    segment = _WHITESPACE.sub("_", part.strip()).lower()
    if not segment:
        raise ValueError(f"A tag part holds no segment characters: {part!r}")

    return segment


def compose_tag(*parts: str) -> str:
    """Joins tag parts into one DearPyGui identifier.

    Each part is lowercased and its whitespace runs become single underscores, so a tag built
    from a runtime name — a sample title, a layer label, a generator — reads the same however
    that name arrives cased or spaced. A part that already holds a composed tag contributes its
    own segments, which is how a child tag extends its parent, and a `StrEnum` member serves as
    a part directly.

    Args:
        *parts: Tag parts to join, in order, each holding at least one segment character.

    Returns:
        str: The parts joined by `TAG_SEPARATOR`.

    Raises:
        ValueError: If called with no part, or if a part holds only whitespace.
    """
    if not parts:
        raise ValueError("A tag needs at least one part")

    return TAG_SEPARATOR.join(_normalize_segment(part) for part in parts)


def identity_part(*parts: str) -> str:
    """Composes the tag part standing for one identity, whatever text its name normalizes to.

    A tag part built from a runtime name arrives lowercased with its whitespace runs collapsed, so
    two names that differ only in case or spacing spell the same segment. Adding this part beside
    the name keeps each identity on a widget of its own, and leaves the name itself in the tag for
    whoever reads a DearPyGui error.

    Args:
        *parts: The pieces the identity is spelled in, in the order they belong.

    Returns:
        str: A digest of the identity, short enough to read beside the name it stands for.
    """
    return identity_digest(*parts, length=TAG_DIGEST_LENGTH)
