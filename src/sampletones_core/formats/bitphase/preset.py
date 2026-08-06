import json
from pathlib import Path
from typing import Final, Sequence, Tuple

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.formats.bitphase.envelopes import features_to_envelopes
from sampletones_core.formats.bitphase.model.instrument import BitphaseInstrumentPreset, NesInstrumentRow
from sampletones_core.formats.bitphase.notes import pitch_to_note_index
from sampletones_core.formats.bitphase.specification.chip import DEFAULT_A4_TUNING, DEFAULT_CPU_FREQUENCY
from sampletones_core.formats.bitphase.specification.instruments import (
    MAX_TONE_ADD,
    MIN_TONE_ADD,
    NO_TONE_OFFSET,
)
from sampletones_core.formats.bitphase.specification.patterns import MAX_NOTE_INDEX, MIN_NOTE_INDEX
from sampletones_core.formats.bitphase.tuning import generate_tuning_table
from sampletones_core.trackers.request import InstrumentExport

PRESET_TUNING_TABLE: Final[Tuple[int, ...]] = generate_tuning_table(
    DEFAULT_CPU_FREQUENCY,
    a4_tuning=DEFAULT_A4_TUNING,
)
PRESET_JSON_INDENT: Final[int] = 2


def _tone_offsets(
    generator: GeneratorName,
    initial_pitch: int,
    contour: Sequence[int],
) -> Tuple[int, ...]:
    """Expresses a semitone contour as the per-tick period offsets a preset carries.

    A preset holds rows alone, so its pitch movement rides in each row's tone offset.
    The offsets are measured against the pitch the slice was reconstructed at, under the
    tuning the NTSC system gives at concert pitch, which is what a freshly created
    Bitphase document plays. The noise channel takes its period from the note rather
    than from a period offset, so its rows hold a flat offset and the note carries the
    pitch.
    """
    if generator == GeneratorName.NOISE:
        return (NO_TONE_OFFSET,) * len(contour)

    base_index = pitch_to_note_index(initial_pitch)
    base_period = PRESET_TUNING_TABLE[base_index]

    offsets = []
    for semitones in contour:
        index = max(MIN_NOTE_INDEX, min(MAX_NOTE_INDEX, base_index + semitones))
        offset = PRESET_TUNING_TABLE[index] - base_period
        offsets.append(max(MIN_TONE_ADD, min(MAX_TONE_ADD, offset)))

    return tuple(offsets)


def instrument_to_preset(request: InstrumentExport) -> BitphaseInstrumentPreset:
    """Builds the single-instrument file Bitphase's instruments panel loads.

    Args:
        request: The generator slice to write.

    Returns:
        BitphaseInstrumentPreset: The instrument to serialize.
    """
    envelopes = features_to_envelopes(
        request.features,
        request.generator,
        loop=request.loop,
    )
    offsets = _tone_offsets(
        request.generator,
        request.features.initial_pitch,
        envelopes.table_rows,
    )
    rows: Tuple[NesInstrumentRow, ...] = tuple(
        row.model_copy(update={"tone_add": offset})
        for row, offset in zip(
            envelopes.rows,
            offsets,
        )
    )

    return BitphaseInstrumentPreset(
        name=request.name,
        loop=envelopes.loop,
        rows=rows,
    )


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
