from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from sampletones_core.bitphase.envelopes import ChannelEnvelopes, features_to_envelopes
from sampletones_core.bitphase.identifiers import format_instrument_id
from sampletones_core.bitphase.model.instrument import BitphaseInstrument
from sampletones_core.bitphase.model.pattern import (
    BitphaseChannel,
    BitphasePattern,
    BitphaseRow,
    NoteCell,
)
from sampletones_core.bitphase.model.project import BitphaseProject
from sampletones_core.bitphase.model.song import BitphaseSong
from sampletones_core.bitphase.model.table import BitphaseTable
from sampletones_core.bitphase.notes import (
    noise_period_to_note_index,
    note_index_to_note_cell,
    pitch_to_note_index,
)
from sampletones_core.bitphase.specification.channels import CHANNEL_LABELS, GENERATOR_NAME_TO_CHANNEL_INDEX
from sampletones_core.bitphase.specification.chip import (
    CPU_FREQUENCIES,
    DEFAULT_A4_TUNING,
    DEFAULT_CHIP_VARIANT,
)
from sampletones_core.bitphase.specification.instruments import (
    MAX_INSTRUMENT_ID,
    MAX_TABLE_ID,
    MIN_INSTRUMENT_ID,
    MIN_TABLE_ID,
)
from sampletones_core.bitphase.specification.patterns import (
    FIRST_PATTERN_ID,
    FULL_VOLUME,
    MAX_PATTERN_LENGTH,
    MIN_PATTERN_LENGTH,
    NO_VOLUME_CHANGE,
    TABLE_COLUMN_OFFSET,
    NoteName,
)
from sampletones_core.bitphase.tuning import generate_tuning_table
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters.slices import iterate_sample_slices
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.trackers.request import InstrumentExport, SampleExport
from sampletones_shared.constants.project import DEFAULT_ROWS_PER_PATTERN, DEFAULT_SPEED

PREVIEW_SPEED = DEFAULT_SPEED
PREVIEW_TRIGGER_ROW = 0
PREVIEW_REST_PATTERN_ID = FIRST_PATTERN_ID + 1
NO_AUTHOR = ""


@dataclass(frozen=True)
class Voice:
    """One built instrument together with the table and the note that triggers it.

    Attributes:
        number: Value a pattern's instrument column carries to play the instrument.
        instrument: The per-tick rows the channel takes on.
        table: The per-tick semitone contour that moves the note.
        generator: The NES channel the slice was reconstructed for.
        initial_pitch: Pitch the slice's contour is measured against.
        ticks: How many ticks the instrument runs before it loops.
    """

    number: int
    instrument: BitphaseInstrument
    table: BitphaseTable
    generator: GeneratorName
    initial_pitch: int
    ticks: int


VoiceTable = Dict[Tuple[str, GeneratorName], Voice]


def _build_voice(
    index: int,
    name: str,
    generator: GeneratorName,
    initial_pitch: int,
    envelopes: ChannelEnvelopes,
) -> Voice:
    """Numbers one generator slice and packages it as an instrument-and-table pair.

    Instruments and tables are numbered alike, so a pattern cell names the same position
    in both columns.

    Raises:
        ValueError: If the position runs past what a pattern column can name.
    """
    number = index + MIN_INSTRUMENT_ID
    if number > MAX_INSTRUMENT_ID:
        raise ValueError(f"Document exceeds the Bitphase limit of {MAX_INSTRUMENT_ID} instruments")

    table_id = index + MIN_TABLE_ID
    if table_id > MAX_TABLE_ID:
        raise ValueError(f"Document exceeds the Bitphase limit of {MAX_TABLE_ID + 1} tables")

    return Voice(
        number=number,
        instrument=BitphaseInstrument(
            id=format_instrument_id(number),
            rows=envelopes.rows,
            loop=envelopes.loop,
            name=name,
        ),
        table=BitphaseTable(
            id=table_id,
            rows=envelopes.table_rows,
            loop=envelopes.loop,
            name=name,
        ),
        generator=generator,
        initial_pitch=initial_pitch,
        ticks=len(envelopes.rows),
    )


def _note_cell(channel_generator: GeneratorName, pitch: int) -> NoteCell:
    """Resolves a pitch to the note column of the channel the row sits on.

    The noise channel reads its note as a period selector, so its pitch takes the
    mapping that reproduces that period; every other channel reads the tuning table.
    """
    if channel_generator == GeneratorName.NOISE:
        return note_index_to_note_cell(noise_period_to_note_index(pitch))

    return note_index_to_note_cell(pitch_to_note_index(pitch))


def _trigger_row(voice: Voice, note: NoteCell, volume: int) -> BitphaseRow:
    return BitphaseRow(
        note=note,
        instrument=voice.number,
        table=voice.table.id + TABLE_COLUMN_OFFSET,
        volume=volume,
    )


def _empty_channels(length: int) -> List[List[BitphaseRow]]:
    return [[BitphaseRow() for _ in range(length)] for _ in CHANNEL_LABELS]


def _to_pattern(
    pattern_id: int,
    length: int,
    channel_rows: Sequence[Sequence[BitphaseRow]],
) -> BitphasePattern:
    channels = tuple(
        BitphaseChannel(rows=tuple(rows), label=label)
        for label, rows in zip(
            CHANNEL_LABELS,
            channel_rows,
        )
    )
    return BitphasePattern(id=pattern_id, length=length, channels=channels)


def _build_song(
    patterns: Tuple[BitphasePattern, ...],
    *,
    speed: int,
    nes_frequency: int,
) -> BitphaseSong:
    chip_frequency = CPU_FREQUENCIES[DEFAULT_CHIP_VARIANT]
    return BitphaseSong(
        patterns=patterns,
        tuning_table=generate_tuning_table(
            chip_frequency,
            a4_tuning=DEFAULT_A4_TUNING,
        ),
        initial_speed=speed,
        chip_frequency=chip_frequency,
        interrupt_frequency=nes_frequency,
    )


def _preview_length(voices: Sequence[Voice]) -> int:
    """Sizes the preview pattern so a full line of it covers the longest instrument."""
    rows = math.ceil(max((voice.ticks for voice in voices), default=0) / PREVIEW_SPEED)
    return max(
        MIN_PATTERN_LENGTH,
        min(MAX_PATTERN_LENGTH, max(rows, DEFAULT_ROWS_PER_PATTERN)),
    )


def _preview_order(voices: Sequence[Voice], length: int) -> Tuple[int, ...]:
    """Spaces the trigger far enough apart for the longest instrument to play through.

    Every order position past the first plays a resting pattern, so an instrument that
    outlasts a single pattern still reaches its end before the trigger comes round again.
    """
    ticks = max((voice.ticks for voice in voices), default=0)
    positions = max(1, math.ceil(ticks / (length * PREVIEW_SPEED)))
    return (FIRST_PATTERN_ID,) + (PREVIEW_REST_PATTERN_ID,) * (positions - 1)


def _preview_patterns(
    voices: Sequence[Voice],
    length: int,
    positions: int,
) -> Tuple[BitphasePattern, ...]:
    channel_rows = _empty_channels(length)
    for voice in voices:
        channel = GENERATOR_NAME_TO_CHANNEL_INDEX[voice.generator]
        note = _note_cell(voice.generator, voice.initial_pitch)
        channel_rows[channel][PREVIEW_TRIGGER_ROW] = _trigger_row(
            voice,
            note,
            FULL_VOLUME,
        )

    patterns = [_to_pattern(FIRST_PATTERN_ID, length, channel_rows)]
    if positions > 1:
        patterns.append(
            _to_pattern(PREVIEW_REST_PATTERN_ID, length, _empty_channels(length)),
        )

    return tuple(patterns)


def sample_to_bitphase(request: SampleExport) -> BitphaseProject:
    """Builds a playable Bitphase document holding one reconstruction's instruments.

    Every generator slice becomes an instrument and the table that carries its pitch
    contour, and one pattern triggers each slice on the channel it was reconstructed
    for, so opening the document and pressing play sounds the reconstruction.

    Args:
        request: The reconstruction's slices.

    Returns:
        BitphaseProject: The document to serialize.

    Raises:
        ValueError: If the reconstruction holds more slices than Bitphase has room for.
    """
    voices = [
        _build_voice(
            index,
            instrument.name,
            instrument.generator,
            instrument.features.initial_pitch,
            features_to_envelopes(
                instrument.features,
                instrument.generator,
                loop=instrument.loop,
            ),
        )
        for index, instrument in enumerate(request.instruments)
    ]

    length = _preview_length(voices)
    order = _preview_order(voices, length)
    patterns = _preview_patterns(voices, length, len(order))

    return BitphaseProject(
        name=request.name,
        author=NO_AUTHOR,
        songs=(_build_song(patterns, speed=PREVIEW_SPEED, nes_frequency=request.nes_frequency),),
        pattern_order=order,
        tables=tuple(voice.table for voice in voices),
        instruments=tuple(voice.instrument for voice in voices),
    )


def instrument_to_bitphase(request: InstrumentExport) -> BitphaseProject:
    """Builds a playable Bitphase document holding one generator slice.

    Args:
        request: The slice to write.

    Returns:
        BitphaseProject: The document to serialize.
    """
    sample = SampleExport(
        name=request.name,
        instruments=(request,),
        nes_frequency=request.nes_frequency,
    )
    return sample_to_bitphase(sample)


def _build_voice_table(project: Project) -> Tuple[List[Voice], VoiceTable]:
    voices: List[Voice] = []
    by_reference: VoiceTable = {}

    for sample_slice in iterate_sample_slices(project):
        envelopes = features_to_envelopes(
            sample_slice.features,
            sample_slice.generator,
            loop=sample_slice.sample.loop,
        )
        voice = _build_voice(
            sample_slice.index,
            sample_slice.instrument_name,
            sample_slice.generator,
            sample_slice.features.initial_pitch,
            envelopes,
        )
        voices.append(voice)
        by_reference[sample_slice.key] = voice

    return voices, by_reference


def _resolve_voice(reference: Instrument, voices: VoiceTable) -> Voice:
    voice = voices.get((reference.sample_id, reference.generator_name))
    if voice is None:
        raise ValueError(
            f"Row references sample '{reference.sample_id}' slice "
            f"'{reference.generator_name}' that has no instrument"
        )

    return voice


def _row_cell(
    row: Row,
    channel_generator: GeneratorName,
    voices: VoiceTable,
) -> BitphaseRow:
    """Converts one tracker line to the Bitphase row that plays it.

    Raises:
        ValueError: If the line references a sample slice that has no instrument.
    """
    volume = row.volume if row.volume is not None else NO_VOLUME_CHANGE
    cell = BitphaseRow(volume=volume)

    match row.command:
        case NoteOff():
            cell = BitphaseRow(
                note=NoteCell(name=int(NoteName.OFF)),
                volume=volume,
            )
        case Instrument() as reference:
            voice = _resolve_voice(reference, voices)
            pitch = voice.initial_pitch + (row.transpose or 0)
            cell = _trigger_row(
                voice,
                _note_cell(channel_generator, pitch),
                volume,
            )
        case None:
            pass

    return cell


def _channel_rows(
    rows: Sequence[Row],
    length: int,
    generator: GeneratorName,
    voices: VoiceTable,
) -> List[BitphaseRow]:
    cells = [_row_cell(row, generator, voices) for row in rows[:length]]
    cells.extend(BitphaseRow() for _ in range(length - len(cells)))
    return cells


def _project_patterns(project: Project, voices: VoiceTable) -> Tuple[BitphasePattern, ...]:
    """Flattens the song's per-channel arrangement into whole-pattern order positions.

    A SampleToNES order frame points every channel at its own pattern, where a Bitphase
    order position names one pattern that spans all channels, so each frame becomes a
    pattern of its own carrying that frame's channels side by side.
    """
    song = project.song
    length = song.rows_per_pattern
    patterns: List[BitphasePattern] = []

    for position, frame in enumerate(song.order):
        channel_rows = _empty_channels(length)
        for generator in GeneratorName.items():
            index = frame.get(generator)
            if index is None:
                continue

            pattern = song.channels[generator].pattern(index)
            if pattern is None:
                continue

            channel = GENERATOR_NAME_TO_CHANNEL_INDEX[generator]
            channel_rows[channel] = _channel_rows(
                pattern.rows,
                length,
                generator,
                voices,
            )

        patterns.append(_to_pattern(position, length, channel_rows))

    return tuple(patterns)


def project_to_bitphase(project: Project) -> BitphaseProject:
    """Maps a project's samples and song onto the Bitphase document IR.

    Args:
        project: The project to write.

    Returns:
        BitphaseProject: The document to serialize.

    Raises:
        ValueError: If the project holds more than Bitphase has room for, or a row
            references a sample slice that has no instrument.
    """
    voices, by_reference = _build_voice_table(project)
    patterns = _project_patterns(project, by_reference)
    settings = project.settings
    info = project.info

    return BitphaseProject(
        name=info.title,
        author=info.author,
        songs=(_build_song(patterns, speed=settings.speed, nes_frequency=settings.nes_frequency),),
        pattern_order=tuple(pattern.id for pattern in patterns),
        tables=tuple(voice.table for voice in voices),
        instruments=tuple(voice.instrument for voice in voices),
    )
