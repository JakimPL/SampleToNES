from bisect import bisect_left
from typing import Dict, List, Mapping, NamedTuple, Tuple

from sampletones_core.constants.general import MAX_TIMER


class NearestPitch(NamedTuple):
    """A divider named as the pitch lying nearest it, beside the steps it stands away.

    Attributes:
        pitch: The pitch whose own divider lies nearest.
        offset: The divider steps from that pitch's own divider to the one named.
    """

    pitch: int
    offset: int


class _Owners(NamedTuple):
    """The distinct dividers a table holds, in ascending order, each beside the pitch standing for it."""

    timers: List[int]
    pitches: Dict[int, int]


def nearest_pitch(
    timer_table: Mapping[int, int],
    divider: int,
) -> NearestPitch:
    """The pitch lying nearest one divider, beside the steps between them.

    A bent note sounds a divider that may belong to no pitch at all. Naming it by the pitch lying
    nearest leaves the fewest steps over: within the table's span, half the widest gap between
    neighboring pitches at most. Pitches sharing a divider sound alike, so the lowest of them
    stands for the group. A divider halfway between two pitches goes to the smaller divider, the
    higher pitch: the lowest pitches all share the clamped top divider, and this keeps a note bent
    down toward it on its own pitch.

    Args:
        timer_table: The divider each pitch sounds at.
        divider: The divider to name.

    Returns:
        NearestPitch: The pitch and the steps the divider stands away from it.

    Raises:
        ValueError: If the table names no pitch.
    """
    return _nearest(divider, _owners(timer_table))


def nearest_pitches(timer_table: Mapping[int, int]) -> Tuple[NearestPitch, ...]:
    """The pitch lying nearest every divider the register holds, by the rule of :func:`nearest_pitch`.

    Args:
        timer_table: The divider each pitch sounds at.

    Returns:
        Tuple[NearestPitch, ...]: One entry per divider from 0 to ``MAX_TIMER``, indexed by the
            divider.

    Raises:
        ValueError: If the table names no pitch.
    """
    owners = _owners(timer_table)
    return tuple(_nearest(divider, owners) for divider in range(MAX_TIMER + 1))


def _owners(timer_table: Mapping[int, int]) -> _Owners:
    pitches: Dict[int, int] = {}
    for pitch in sorted(timer_table):
        pitches.setdefault(timer_table[pitch], pitch)

    if not pitches:
        raise ValueError("a timer table names at least one pitch to measure a divider from")

    return _Owners(timers=sorted(pitches), pitches=pitches)


def _nearest(
    divider: int,
    owners: _Owners,
) -> NearestPitch:
    position = bisect_left(owners.timers, divider)
    neighbors = owners.timers[max(position - 1, 0) : position + 1]
    timer = min(neighbors, key=lambda neighbor: (abs(divider - neighbor), neighbor))
    return NearestPitch(pitch=owners.pitches[timer], offset=divider - timer)
