from typing import Optional

from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions.tonal import bend_steps

NO_BEND_STEP = 0


def bend_envelope(pitch: Optional[Envelope[int]], hi_pitch: Optional[Envelope[int]]) -> Envelope[int]:
    """The timer steps a slice's two bend dimensions move its note by, one value per tick.

    A bend reaches a register as one divider whichever split of fine and coarse steps stated
    it, and this is that reading taken from the envelopes — the dimension-side twin of
    ``TonalExporter.read_timer_offsets``. Each dimension advances on a counter of its own, so
    the pair states an offset for as long as the longer of them runs, and a dimension standing
    past its end reads at the value it holds there.

    Args:
        pitch: The dimension carrying one step per unit, where the channel offers it.
        hi_pitch: The dimension carrying sixteen steps per unit, where the channel offers it.

    Returns:
        Envelope[int]: The steps each tick stands away from its note, written where either
            dimension carries items.
    """
    fine = pitch if pitch is not None else Envelope[int]()
    coarse = hi_pitch if hi_pitch is not None else Envelope[int]()
    ticks = max(len(fine.items), len(coarse.items))
    if not ticks:
        return Envelope[int]()

    items = tuple(bend_steps(_step(fine, tick), _step(coarse, tick)) for tick in range(ticks))
    return Envelope[int](items=items, loop_point=_repeat_point(fine, coarse))


def _step(envelope: Envelope[int], tick: int) -> int:
    """The value a dimension carries at a tick, which is nothing where it writes no items."""
    value = envelope.at(tick)
    return NO_BEND_STEP if value is None else value


def _repeat_point(fine: Envelope[int], coarse: Envelope[int]) -> Optional[int]:
    """The point the pair circles from, which is the earliest either dimension states."""
    points = [envelope.loop_point for envelope in (fine, coarse) if envelope.loop_point is not None]
    if not points:
        return None

    return min(points)
