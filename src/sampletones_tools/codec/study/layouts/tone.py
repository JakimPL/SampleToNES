from typing import Dict, Final, List, Sequence, Tuple

from sampletones_core.timers.nearest import NearestPitch
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.channel import TonePlanes
from sampletones_player.compression.planes.rebuild import tone_dividers
from sampletones_player.registers.dividers import anchored_pitches
from sampletones_player.specification.binary import unsigned_byte
from sampletones_tools.codec.study.layouts.layout import Anchor, BendForm, PlaneLayout

FLAG_BIT: Final[int] = 0x80


def layout_anchors(
    dividers: Sequence[int],
    notes: bytes,
    pitches: PitchTable,
    anchor: Anchor,
) -> Tuple[NearestPitch, ...]:
    """The index each tick's value plane names, beside the bend that reaches its divider from there.

    Args:
        dividers: The divider each tick sounds.
        notes: The note each tick's frame names.
        pitches: The timer each pitch sounds at.
        anchor: What the value plane names.

    Returns:
        Tuple[NearestPitch, ...]: One index and bend per tick.

    Raises:
        ValueError: If the dividers and the notes cover different ticks.
    """
    match anchor:
        case Anchor.NEAREST:
            return tuple(pitches.nearest[divider] for divider in dividers)
        case Anchor.NAMED:
            anchors = anchored_pitches(notes, dividers, _timer_table(pitches))
            return tuple(_counted(divider, pitches.index(pitch), pitches) for divider, pitch in zip(dividers, anchors))


def _timer_table(pitches: PitchTable) -> Dict[int, int]:
    """The timer each pitch of the table sounds at, keyed by the pitch."""
    return {pitches.pitch(index): timer for index, timer in enumerate(pitches.timers)}


def _counted(
    divider: int,
    index: int,
    pitches: PitchTable,
) -> NearestPitch:
    return NearestPitch(pitch=index, offset=divider - pitches.timers[index])


def bend_flags(
    anchored: Sequence[NearestPitch],
    form: BendForm,
) -> Tuple[bool, ...]:
    """Which ticks carry a bend byte where the bend plane holds only the ticks flagged.

    Args:
        anchored: The index and bend each tick names.
        form: How the bend plane covers the ticks.

    Returns:
        Tuple[bool, ...]: One flag per tick; a dense plane flags every tick.
    """
    match form:
        case BendForm.DENSE:
            return (True,) * len(anchored)
        case BendForm.FLAGGED_TICKS:
            return tuple(pitch.offset != 0 for pitch in anchored)
        case BendForm.FLAGGED_NOTES:
            return _note_flags(anchored)


def _note_flags(anchored: Sequence[NearestPitch]) -> Tuple[bool, ...]:
    """Flags each run of one index from its first bent tick to its last."""
    flags: List[bool] = [False] * len(anchored)
    start = 0
    for end in range(1, len(anchored) + 1):
        if end < len(anchored) and anchored[end].pitch == anchored[start].pitch:
            continue

        bent = [tick for tick in range(start, end) if anchored[tick].offset != 0]
        if bent:
            flags[bent[0] : bent[-1] + 1] = [True] * (bent[-1] - bent[0] + 1)

        start = end

    return tuple(flags)


def tone_planes(
    planes: TonePlanes,
    notes: bytes,
    pitches: PitchTable,
    layout: PlaneLayout,
) -> Tuple[bytes, bytes, bytes]:
    """A tone channel's control, value and bend planes written under a layout.

    Args:
        planes: The channel's planes as the production codec separates them.
        notes: The note each tick's frame names.
        pitches: The timer each pitch sounds at.
        layout: How the divider is written across the value and the bend.

    Returns:
        Tuple[bytes, bytes, bytes]: The control, value and bend planes; a flagged bend plane holds
            only the ticks its value plane flags.

    Raises:
        ValueError: If a flagged layout meets a table whose indices reach the flag bit.
    """
    anchored = layout_anchors(tone_dividers(planes, pitches.timers), notes, pitches, layout.anchor)
    flags = bend_flags(anchored, layout.form)
    bend = bytes(unsigned_byte(pitch.offset) for pitch, flag in zip(anchored, flags) if flag)
    if layout.form is BendForm.DENSE:
        return planes.control, bytes(pitch.pitch for pitch in anchored), bend

    if len(pitches.timers) > FLAG_BIT:
        raise ValueError(f"a flagged value names at most {FLAG_BIT} pitches, and the table holds {len(pitches.timers)}")

    value = bytes(pitch.pitch | FLAG_BIT if flag else pitch.pitch for pitch, flag in zip(anchored, flags))
    return planes.control, value, bend
