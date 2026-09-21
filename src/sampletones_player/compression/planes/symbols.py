from typing import FrozenSet, List, Tuple

from sampletones_player.specification.planes import SINGLE_TICK, PlaneForm


def pack_plane(
    played: bytes,
    form: PlaneForm,
    *,
    boundaries: FrozenSet[int],
) -> bytes:
    """The symbols a plane plays, each a value and the ticks it repeats for.

    A run of one value becomes one symbol for as many ticks as the form's count reaches, and a
    longer run becomes as many symbols as that takes. A tick the song re-enters on begins a
    symbol of its own, so the plane stands at a symbol's first byte wherever a token may start.

    Args:
        played: The values the plane plays.
        form: How the plane's byte divides.
        boundaries: The ticks a symbol begins on, beyond the plane's first.

    Returns:
        bytes: The symbols, in the order they are played.

    Raises:
        ValueError: If a value the plane plays carries fixed bits other than the form's.
    """
    symbols = bytearray()
    for start, length in _runs(played, boundaries=boundaries):
        held = length
        while held:
            repeats = min(held, form.repeats)
            symbols.append(form.symbol(played[start], repeats))
            held -= repeats

    return bytes(symbols)


def unpack_plane(
    symbols: bytes,
    form: PlaneForm,
) -> bytes:
    """The values a run of symbols plays, one per tick.

    Args:
        symbols: The symbols the plane is written as.
        form: How the plane's byte divides.

    Returns:
        bytes: The values, one per tick.
    """
    values = bytearray()
    for symbol in symbols:
        values.extend((form.value(symbol),) * form.repeated(symbol))

    return bytes(values)


def symbol_boundaries(
    played: bytes,
    form: PlaneForm,
    *,
    boundaries: FrozenSet[int],
) -> FrozenSet[int]:
    """Where the ticks a token starts on stand once the plane is packed.

    A packed plane is read a symbol at a time, so the parse counts symbols where it counted
    ticks and a boundary reaches it as the symbol the tick begins.

    Args:
        played: The values the plane plays.
        form: How the plane's byte divides.
        boundaries: The ticks a token starts on, beyond the plane's first.

    Returns:
        FrozenSet[int]: The symbols those ticks begin.
    """
    positions = {}
    symbol = 0
    for start, length in _runs(played, boundaries=boundaries):
        positions[start] = symbol
        symbol += -(-length // form.repeats)

    return frozenset(positions[tick] for tick in boundaries if tick in positions)


def _runs(
    played: bytes,
    *,
    boundaries: FrozenSet[int],
) -> Tuple[Tuple[int, int], ...]:
    """Where each run of one value begins and how many ticks it lasts, cut at every boundary."""
    runs: List[Tuple[int, int]] = []
    start = 0
    for tick in range(SINGLE_TICK, len(played)):
        if played[tick] != played[start] or tick in boundaries:
            runs.append((start, tick - start))
            start = tick

    if played:
        runs.append((start, len(played) - start))

    return tuple(runs)
