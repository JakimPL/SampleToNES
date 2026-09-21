import json
from pathlib import Path
from typing import Final, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters.bend import bend_envelope
from sampletones_core.exporters.feature import Features
from sampletones_core.exports.request import InstrumentExport
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.envelopes import ChannelEnvelopes, features_to_envelopes
from sampletones_core.formats.bitphase.macros import macro, stored_envelope
from sampletones_core.formats.bitphase.model.instrument import BitphaseInstrumentPreset
from sampletones_core.formats.bitphase.notes import pitch_to_note_index
from sampletones_core.formats.bitphase.pitch import contour_period, sounding_offset
from sampletones_core.formats.bitphase.specification.instruments import NO_TONE_OFFSET
from sampletones_core.formats.bitphase.specification.macros import NesMacroField
from sampletones_core.formats.bitphase.tuning import DEFAULT_TUNING_TABLE

PRESET_JSON_INDENT: Final[int] = 2


def _tone_offsets(
    features: Features,
    channel: ChannelName,
    contour: Sequence[int],
) -> Tuple[int, ...]:
    """Expresses a slice's pitch movement as the per-tick period offsets a preset carries.

    A preset holds macros alone, so the movement a table would drive rides in the tone offset
    each tick takes, beside the bend the slice sounds. The offsets are measured against the
    pitch the slice was reconstructed at, under the tuning the NTSC system gives at concert
    pitch, which is what a freshly created Bitphase document plays. The noise channel takes its
    period from the note rather than from a period offset, so its offsets stay flat and the note
    carries the pitch.
    """
    if channel == ChannelName.NOISE:
        return (NO_TONE_OFFSET,) * len(contour)

    base_index = pitch_to_note_index(features.initial_pitch)
    base_period = DEFAULT_TUNING_TABLE[base_index]
    bend = stored_envelope(FeatureKey.PITCH, bend_envelope(features.pitch, features.hi_pitch))

    offsets = []
    for tick, semitones in enumerate(contour):
        moved = contour_period(base_index, semitones) - base_period
        offsets.append(sounding_offset(base_period, moved + _value(bend, tick)))

    return tuple(offsets)


def instrument_to_preset(request: InstrumentExport) -> BitphaseInstrumentPreset:
    """Builds the single-instrument file Bitphase's instruments panel loads.

    Args:
        request: The channel slice to write.

    Returns:
        BitphaseInstrumentPreset: The instrument to serialize.
    """
    envelopes = features_to_envelopes(
        request.features,
        request.channel,
    )
    offsets = _tone_offsets(
        request.features,
        request.channel,
        _contour(envelopes),
    )

    return BitphaseInstrumentPreset(
        name=request.name,
        macros={
            **envelopes.macros,
            NesMacroField.TONE_ADD: macro(Envelope[int](items=offsets, loop_point=envelopes.table_loop)),
        },
    )


def _contour(envelopes: ChannelEnvelopes) -> Tuple[int, ...]:
    """The semitone steps a preset states an offset for, one per tick the instrument runs.

    A document moves the note through a table that advances on a counter of its own, where a
    preset carries the movement in the offsets themselves, so the contour is read out to the
    ticks the slice describes.
    """
    contour = Envelope[int](items=envelopes.table_rows, loop_point=envelopes.table_loop)
    return tuple(_value(contour, tick) for tick in range(envelopes.ticks))


def _value(envelope: Envelope[int], tick: int) -> int:
    """The value a dimension stands at on a tick, which is nothing where it writes none."""
    value = envelope.at(tick)
    return NO_TONE_OFFSET if value is None else value


def write_preset(destination: Path, preset: BitphaseInstrumentPreset) -> None:
    """Writes a Bitphase instrument preset to disk.

    The file is indented the way Bitphase writes its own, so a preset dropped into the
    tracker's preset tree reads like the ones already there.

    Args:
        destination: The file to write.
        preset: The instrument to serialize.

    Raises:
        OSError: If the destination cannot be written.
    """
    payload = json.dumps(
        preset.model_dump(mode="json", by_alias=True),
        indent=PRESET_JSON_INDENT,
    )
    destination.write_text(payload, encoding="utf-8")
