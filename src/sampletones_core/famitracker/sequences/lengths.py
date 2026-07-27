from typing import Dict, List, Tuple

from sampletones_core.famitracker.specification.sequences import (
    MAX_SEQUENCE_ITEMS,
    SequenceKind,
)
from sampletones_shared.logger import logger


def _resize(items: Tuple[int, ...], length: int) -> Tuple[int, ...]:
    """Brings a sequence to a length, repeating its final value when it falls short."""
    return items[:length] + items[-1:] * (length - len(items))


def _common_length(lengths: List[int], loop: bool) -> int:
    """Chooses the length every populated sequence of an instrument shares.

    A looping instrument takes the shortest length, which drops the trailing note-off
    volume item the loop would otherwise sound once per cycle; a one-shot takes the
    longest, so each shorter dimension holds its final value to the end. The result
    stays within the item count FamiTracker stores, so an envelope longer than that
    keeps its opening items and the rest is reported as dropped.

    Args:
        lengths: The item counts of the populated dimensions.
        loop: Whether the instrument loops while its note is held.

    Returns:
        int: The shared item count, at most ``MAX_SEQUENCE_ITEMS``.
    """
    length = min(lengths) if loop else max(lengths)
    if length <= MAX_SEQUENCE_ITEMS:
        return length

    logger.warning(
        f"Instrument envelope of {length} items keeps its first {MAX_SEQUENCE_ITEMS}, "
        f"the most FamiTracker stores in a sequence"
    )
    return MAX_SEQUENCE_ITEMS


def equalize_lengths(
    items_by_kind: Dict[SequenceKind, Tuple[int, ...]],
    loop: bool,
) -> Dict[SequenceKind, Tuple[int, ...]]:
    """Brings every populated sequence of an instrument to one common length.

    FamiTracker advances each sequence on its own per-tick counter, so dimensions of
    unequal length pull apart: a looping instrument's envelopes slip by a tick per
    cycle, and a one-shot's shorter dimensions expire while its volume still sounds.

    Args:
        items_by_kind: The per-kind item tuples, empty for a disabled dimension.
        loop: Whether the instrument loops while its note is held.

    Returns:
        Dict[SequenceKind, Tuple[int, ...]]: The items with every populated kind at
            one length, leaving disabled kinds empty.
    """
    lengths = [len(items) for items in items_by_kind.values() if items]
    if not lengths:
        return items_by_kind

    length = _common_length(lengths, loop)
    return {kind: _resize(items, length) if items else items for kind, items in items_by_kind.items()}
