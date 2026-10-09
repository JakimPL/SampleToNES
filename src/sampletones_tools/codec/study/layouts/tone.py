from typing import Dict, Sequence, Tuple

from sampletones_core.timers.nearest import NearestPitch
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.flags import flagged_value, note_flags
from sampletones_player.compression.planes.rebuild import tone_dividers
from sampletones_player.registers.dividers import anchored_pitches
from sampletones_player.specification.binary import unsigned_byte
from sampletones_player.specification.planes import SILENT_PITCH_INDEX
from sampletones_tools.codec.study.layouts.layout import Anchor, BendForm, PlaneLayout


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
            return note_flags([pitch.pitch for pitch in anchored], [pitch.offset for pitch in anchored])


def tone_planes(
    planes: Tuple[bytes, ...],
    notes: bytes,
    pitches: PitchTable,
    layout: PlaneLayout,
) -> Tuple[bytes, ...]:
    """A tone channel's planes written under a layout, the divider read across value and bend.

    A tick naming the index that stands for silence keeps it, since a layout moves where a
    divider is written rather than whether the channel sounds.

    Args:
        planes: The channel's planes as the production codec separates them.
        notes: The note each tick's frame names.
        pitches: The timer each pitch sounds at.
        layout: How the divider is written across the value and the bend.

    Returns:
        Tuple[bytes, ...]: The channel's planes as the song block writes them; a flagged bend
            plane holds only the ticks its value plane flags.

    Raises:
        ValueError: If a flagged layout meets an index reaching the flag's bit.
    """
    *timbre, named, offsets = planes
    resting = tuple(pitch == SILENT_PITCH_INDEX for pitch in named)
    anchored = layout_anchors(tone_dividers(named, offsets, pitches.timers), notes, pitches, layout.anchor)
    flags = tuple(flag and not rest for flag, rest in zip(bend_flags(anchored, layout.form), resting, strict=True))
    bend = bytes(unsigned_byte(pitch.offset) for pitch, flag in zip(anchored, flags) if flag)
    if layout.form is BendForm.DENSE:
        spelled = bytes(
            SILENT_PITCH_INDEX if rest else pitch.pitch for rest, pitch in zip(resting, anchored, strict=True)
        )
        return (*timbre, spelled, bend)

    value = bytes(
        SILENT_PITCH_INDEX if rest else flagged_value(pitch.pitch, flag)
        for rest, pitch, flag in zip(resting, anchored, flags, strict=True)
    )
    return (*timbre, value, bend)
