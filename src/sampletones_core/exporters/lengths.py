from collections.abc import Hashable
from typing import Dict, List, Optional, Tuple, TypeVar

from sampletones_shared.logger import logger

EnvelopeKey = TypeVar("EnvelopeKey", bound=Hashable)


def _resize(items: Tuple[int, ...], length: int) -> Tuple[int, ...]:
    """Brings a sequence to a length, repeating its final value when it falls short."""
    return items[:length] + items[-1:] * (length - len(items))


def _limited_length(length: int, limit: Optional[int]) -> int:
    """Brings a length within what the target format stores, reporting what that drops."""
    if limit is None or length <= limit:
        return length

    logger.warning(f"Instrument envelope of {length} items keeps its first {limit}, the most the format holds")
    return limit


def _common_length(lengths: List[int], loop: bool, limit: Optional[int]) -> int:
    """Chooses the length every populated dimension of an instrument shares.

    A looping instrument takes the shortest length, which drops the trailing note-off
    volume item the loop would otherwise sound once per cycle; a one-shot takes the
    longest, so each shorter dimension holds its final value to the end. A ``limit``
    caps the result, so an envelope longer than the target format stores keeps its
    opening items and the rest is reported as dropped.

    Args:
        lengths: The item counts of the populated dimensions.
        loop: Whether the instrument loops while its note is held.
        limit: The most items the target format stores, or ``None`` when it is unbounded.

    Returns:
        int: The shared item count, at most ``limit`` where one applies.
    """
    return _limited_length(min(lengths) if loop else max(lengths), limit)


def limit_lengths(
    items_by_kind: Dict[EnvelopeKey, Tuple[int, ...]],
    *,
    limit: int,
) -> Dict[EnvelopeKey, Tuple[int, ...]]:
    """Keeps each dimension's opening items, as many as the target format stores.

    Every dimension stands at its own length, which is what a player that sustains an
    exhausted envelope's final value reads: the envelope describes the frames it covers
    and the last value it wrote governs the rest.

    Args:
        items_by_kind: The per-dimension item tuples, empty for a dimension the channel
            leaves unused.
        limit: The most items the target format stores.

    Returns:
        Dict[EnvelopeKey, Tuple[int, ...]]: The items with every dimension within the limit.
    """
    return {
        kind: items[
            : _limited_length(
                len(items),
                limit,
            )
        ]
        for kind, items in items_by_kind.items()
    }


def equalize_lengths(
    items_by_kind: Dict[EnvelopeKey, Tuple[int, ...]],
    loop: bool,
    *,
    limit: Optional[int] = None,
) -> Dict[EnvelopeKey, Tuple[int, ...]]:
    """Brings every populated dimension of an instrument to one common length.

    A tracker advances each dimension on its own per-tick counter, so dimensions of
    unequal length pull apart: a looping instrument's envelopes slip by a tick per
    cycle, and a one-shot's shorter dimensions expire while its volume still sounds.

    Args:
        items_by_kind: The per-dimension item tuples, empty for a dimension the channel
            leaves unused.
        loop: Whether the instrument loops while its note is held.
        limit: The most items the target format stores, or ``None`` when it is unbounded.

    Returns:
        Dict[EnvelopeKey, Tuple[int, ...]]: The items with every populated dimension at
            one length, leaving unused dimensions empty.
    """
    lengths = [len(items) for items in items_by_kind.values() if items]
    if not lengths:
        return items_by_kind

    length = _common_length(lengths, loop, limit)
    return {kind: _resize(items, length) if items else items for kind, items in items_by_kind.items()}
