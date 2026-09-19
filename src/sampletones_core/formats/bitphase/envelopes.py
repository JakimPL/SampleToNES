from dataclasses import dataclass
from typing import Dict, Tuple

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters.feature import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.macros import macro, stored_envelope
from sampletones_core.formats.bitphase.model.instrument import InstrumentMacro
from sampletones_core.formats.bitphase.notes import noise_arpeggio_to_table_offset
from sampletones_core.formats.bitphase.specification.instruments import (
    FLAT_PULSE_WIDTH,
    LOOP_FROM_START,
    MAX_VOLUME_OR_RATE,
    NO_TABLE_OFFSET,
    NOISE_MODE_LONG,
    NOISE_MODE_SHORT,
    SILENT_VOLUME,
)
from sampletones_core.formats.bitphase.specification.macros import NesMacroField

SILENT_VOLUME_ENVELOPE = Envelope[int](items=(SILENT_VOLUME,))
HELD_VOLUME_ENVELOPE = Envelope[int](items=(MAX_VOLUME_OR_RATE,))
FLAT_CONTOUR = Envelope[int](items=(NO_TABLE_OFFSET,))

MacroBag = Dict[NesMacroField, InstrumentMacro]


@dataclass(frozen=True)
class ChannelEnvelopes:
    """One channel slice expressed the way Bitphase plays it back.

    An instrument's macros and its table advance on per-tick counters of their own, so each
    carries the length and the repeat point its own dimension asks for.

    Attributes:
        macros: One macro per instrument field the slice decides.
        table_rows: Semitone offsets, one per engine tick.
        table_loop: Step the contour circles from once it runs off the end.
        ticks: Ticks the longest dimension describes.
    """

    macros: MacroBag
    table_rows: Tuple[int, ...]
    table_loop: int
    ticks: int


def _pulse_width(channel: ChannelName, duty_cycle: int) -> int:
    """Reads a duty-cycle item as the field the channel uses it for.

    A square channel takes it as the duty itself; the noise channel takes any nonzero
    value as its short LFSR mode; the triangle channel plays one fixed waveform.
    """
    match channel:
        case ChannelName.PULSE1 | ChannelName.PULSE2:
            return duty_cycle
        case ChannelName.NOISE:
            return NOISE_MODE_SHORT if duty_cycle else NOISE_MODE_LONG
        case ChannelName.TRIANGLE:
            return FLAT_PULSE_WIDTH


def _table_offset(channel: ChannelName, arpeggio: int) -> int:
    if channel == ChannelName.NOISE:
        return noise_arpeggio_to_table_offset(arpeggio)

    return arpeggio


def _volume_envelope(features: Features) -> Envelope[int]:
    """The levels an instrument writes, which a slice leaving its volume alone holds full.

    Bitphase combines each row's level with the pattern's volume column, and a full level
    comes out at the column's own level, so an instrument holding one sounds at whatever
    level the channel carries.
    """
    volume = features.envelopes.get(FeatureKey.VOLUME, Envelope[int]())
    if volume.written:
        return stored_envelope(FeatureKey.VOLUME, volume)

    return HELD_VOLUME_ENVELOPE


def _waveform_envelope(features: Features, channel: ChannelName) -> Envelope[int]:
    """The waveform values a channel takes, which a slice leaving its duty alone holds flat."""
    duty_cycle = stored_envelope(
        FeatureKey.DUTY_CYCLE,
        features.envelopes.get(FeatureKey.DUTY_CYCLE, Envelope[int]()),
    )
    items = duty_cycle.items or (FLAT_PULSE_WIDTH,)
    return duty_cycle.with_items(tuple(_pulse_width(channel, item) for item in items))


def _contour(features: Features, channel: ChannelName) -> Envelope[int]:
    """The semitone steps the table moves the note by, flat where the slice states none."""
    arpeggio = features.envelopes.get(FeatureKey.ARPEGGIO, Envelope[int]())
    if not arpeggio.written:
        return FLAT_CONTOUR

    return arpeggio.with_items(tuple(_table_offset(channel, step) for step in arpeggio.items))


def _silent_slice(features: Features, channel: ChannelName) -> ChannelEnvelopes:
    """The smallest instrument Bitphase plays, which is what a slice describing no frame writes."""
    return ChannelEnvelopes(
        macros=_macro_bag(SILENT_VOLUME_ENVELOPE, features, channel),
        table_rows=FLAT_CONTOUR.items,
        table_loop=LOOP_FROM_START,
        ticks=0,
    )


def _macro_bag(volume: Envelope[int], features: Features, channel: ChannelName) -> MacroBag:
    """The fields the slice decides, the triangle channel leaving its one waveform alone."""
    macros = {NesMacroField.VOLUME_OR_RATE: macro(volume)}
    if channel != ChannelName.TRIANGLE:
        macros[NesMacroField.PULSE_WIDTH] = macro(_waveform_envelope(features, channel))

    return macros


def features_to_envelopes(
    features: Features,
    channel: ChannelName,
) -> ChannelEnvelopes:
    """Converts one channel slice's envelopes into the macros and table Bitphase reads it from.

    Volume becomes the instrument's per-tick level, the duty cycle becomes the channel's
    waveform field, and the arpeggio becomes the table contour that moves the note. Each
    keeps the length and the repeat point it was written at, so a dimension holding one
    value all through costs that one value.

    A slice describing no frame comes back as the one silent value that is the smallest
    instrument Bitphase plays.

    Args:
        features: The per-dimension envelopes describing the slice.
        channel: The NES channel the slice was reconstructed for.

    Returns:
        ChannelEnvelopes: The macros, contour and repeat points describing the slice.
    """
    if not features.frame_count:
        return _silent_slice(features, channel)

    contour = _contour(features, channel)
    macros = _macro_bag(_volume_envelope(features), features, channel)

    return ChannelEnvelopes(
        macros=macros,
        table_rows=contour.items,
        table_loop=_repeat_point(contour),
        ticks=_ticks(macros, contour),
    )


def _repeat_point(envelope: Envelope[int]) -> int:
    """The step a dimension circles from, which is its last where it states no point of its own."""
    if envelope.loop_point is not None:
        return envelope.loop_point

    return len(envelope.items) - 1


def _ticks(macros: MacroBag, contour: Envelope[int]) -> int:
    """How long the instrument runs before every dimension it writes stands at its end."""
    lengths = [len(written.values) for written in macros.values()]
    return max(lengths + [len(contour.items)])
