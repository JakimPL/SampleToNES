import re
from typing import Final, NamedTuple, Tuple

from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key.text import TextKey
from sampletones_application.tags.compose import TAG_SEPARATOR, compose_tag
from sampletones_shared.exceptions import MalformedTextKeyError

TEXT_KEY_SEGMENT_COUNT: Final[int] = len(TextKey._fields)
TEXT_KEY_GRAMMAR: Final[str] = compose_tag(*TextKey._fields)

_SEGMENT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


class _SegmentType(NamedTuple):
    name: str
    values: Tuple[str, ...]


_SEGMENT_TYPES: Final[Tuple[_SegmentType, ...]] = (
    _SegmentType(name="page", values=tuple(page.value for page in Page)),
    _SegmentType(name="panel", values=tuple(panel.value for panel in Panel if panel.value)),
    _SegmentType(name="text type", values=tuple(text_type.value for text_type in TextType)),
)


def _validate_segment_shape(key: str, position: int, segment: str) -> None:
    if _SEGMENT_PATTERN.match(segment):
        return

    raise MalformedTextKeyError(
        f"Malformed text key {key!r}: segment {position} {segment!r} must spell a slug of lowercase "
        "letters and digits, grouped by single underscores"
    )


def _validate_segment_member(
    key: str,
    position: int,
    segment: str,
    segment_type: _SegmentType,
) -> None:
    if segment in segment_type.values:
        return

    raise MalformedTextKeyError(
        f"Malformed text key {key!r}: segment {position} {segment!r} must name a {segment_type.name}, "
        f"one of {', '.join(segment_type.values)}"
    )


def validate_text_key(key: str) -> None:
    """Checks that a string spells a text key the language file can hold.

    A text key names its page, panel, text type, and element in that order, joined by
    `TAG_SEPARATOR` — the spelling `en.yaml` uses. The first three segments name members of `Page`,
    `Panel`, and `TextType`; the element segment is checked as a slug here, and the `language-keys`
    hook confirms it names a member of a concrete element enum, since the hook sees every element
    enum at once.

    Args:
        key: Text key to check.

    Raises:
        MalformedTextKeyError: If the key holds a segment count other than
            `TEXT_KEY_SEGMENT_COUNT`, a segment outside the slug alphabet, or a page, panel, or
            text type absent from the hierarchy.
    """
    segments = key.split(TAG_SEPARATOR)
    if len(segments) != TEXT_KEY_SEGMENT_COUNT:
        raise MalformedTextKeyError(
            f"Malformed text key {key!r}: its segment count is {len(segments)}, where a text key holds "
            f"exactly {TEXT_KEY_SEGMENT_COUNT} segments, spelled {TEXT_KEY_GRAMMAR}"
        )

    for position, segment in enumerate(segments, start=1):
        _validate_segment_shape(key, position, segment)

    for position, (segment, segment_type) in enumerate(
        zip(segments, _SEGMENT_TYPES, strict=False),
        start=1,
    ):
        _validate_segment_member(key, position, segment, segment_type)
