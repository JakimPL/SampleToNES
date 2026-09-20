from typing import Final, Tuple

from sampletones_player.specification.binary import MAX_BYTE_VALUE
from sampletones_shared.constants.general import BITS_PER_BYTE
from sampletones_tools.codec.study.packing.form import NO_BITS, WHOLE_BYTE, PlaneForm

FORM_SIZE: Final[int] = 2


def fitted_form(plane: bytes) -> PlaneForm:
    """The narrowest form the plane's own values allow.

    A register fixes some of a byte's bits for every song, and a song fixes more of its own: a
    triangle channel names its counter control in every tick, and a bass line reaching only the
    low notes leaves the index's top bits standing at zero. Whichever bits the plane never turns
    over are free, and the longest run of them carries the repeat count.

    Args:
        plane: The values the plane plays.

    Returns:
        PlaneForm: The form, a plane turning over every bit taking its whole byte.
    """
    if not plane:
        return WHOLE_BYTE

    count_mask = _longest_run(_settled_bits(plane))
    return PlaneForm(
        value_mask=MAX_BYTE_VALUE ^ count_mask,
        value_or=plane[0] & count_mask,
    )


def _settled_bits(plane: bytes) -> int:
    """The bits every value of the plane agrees on."""
    settled = MAX_BYTE_VALUE
    first = plane[0]
    for value in plane:
        settled &= MAX_BYTE_VALUE ^ (value ^ first)

    return settled


def _longest_run(settled: int) -> int:
    """The longest run of set bits in ``settled``, as the mask it covers."""
    runs: Tuple[int, ...] = tuple(_runs(settled))
    if not runs:
        return NO_BITS

    return max(runs, key=_width)


def _runs(settled: int) -> Tuple[int, ...]:
    found = []
    run = NO_BITS
    for bit in range(BITS_PER_BYTE):
        position = 1 << bit
        if settled & position:
            run |= position
            continue

        if run:
            found.append(run)

        run = NO_BITS

    if run:
        found.append(run)

    return tuple(found)


def _width(run: int) -> int:
    return bin(run).count("1")
