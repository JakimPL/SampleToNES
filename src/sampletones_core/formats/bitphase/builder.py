import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import SILENT_VOLUME
from sampletones_core.exporters.slices import iterate_sample_slices
from sampletones_core.formats.bitphase.envelopes import (
    ChannelEnvelopes,
    features_to_envelopes,
)
from sampletones_core.formats.bitphase.identifiers import format_instrument_id
from sampletones_core.formats.bitphase.model.instrument import BitphaseInstrument
from sampletones_core.formats.bitphase.model.pattern import (
    BitphaseChannel,
    BitphasePattern,
    BitphaseRow,
    EffectCell,
    NoteCell,
)
from sampletones_core.formats.bitphase.model.project import BitphaseProject
from sampletones_core.formats.bitphase.model.song import BitphaseSong
from sampletones_core.formats.bitphase.model.table import BitphaseTable
from sampletones_core.formats.bitphase.notes import (
    noise_period_to_note_index,
    note_index_to_note_cell,
    pitch_to_note_index,
)
from sampletones_core.formats.bitphase.specification.channels import (
    CHANNEL_LABELS,
    CHANNEL_TO_INDEX,
    ChannelIndex,
)
from sampletones_core.formats.bitphase.specification.chip import (
    CPU_FREQUENCIES,
    DEFAULT_A4_TUNING,
    DEFAULT_CHIP_VARIANT,
    MAX_INITIAL_SPEED,
    MIN_INITIAL_SPEED,
)
from sampletones_core.formats.bitphase.specification.effects import (
    NO_EFFECT_PARAMETER,
    SPEED_EFFECT_DELAY,
    EffectId,
)
from sampletones_core.formats.bitphase.specification.instruments import (
    LOOP_FROM_START,
    MAX_INSTRUMENT_ID,
    MAX_TABLE_ID,
    MIN_INSTRUMENT_ID,
    MIN_TABLE_ID,
)
from sampletones_core.formats.bitphase.specification.patterns import (
    FIRST_PATTERN_ID,
    FULL_VOLUME,
    MAX_PATTERN_LENGTH,
    MIN_PATTERN_LENGTH,
    NO_VOLUME_CHANGE,
    TABLE_COLUMN_OFFSET,
    VOLUME_OFF,
    NoteName,
)
from sampletones_core.formats.bitphase.tuning import generate_tuning_table
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.timing import Groove, Metre, RowRate, calculate_groove
from sampletones_core.trackers.request import InstrumentExport, SampleExport
from sampletones_shared.constants.project import DEFAULT_ROWS_PER_PATTERN, DEFAULT_SPEED

PREVIEW_SPEED = DEFAULT_SPEED
PREVIEW_TRIGGER_ROW = 0
PREVIEW_REST_PATTERN_ID = FIRST_PATTERN_ID + 1
NO_AUTHOR = ""

GROOVE_CHANNEL = ChannelIndex.DPCM
GROOVE_TRIGGER_ROW = 0
GROOVE_TABLE_NAME = "Groove"
GROOVE_TABLE_COUNT = 1


@dataclass(frozen=True)
class Voice:
    """One built instrument together with the table and the note that triggers it.

    Attributes:
        number: Value a pattern's instrument column carries to play the instrument.
        instrument: The per-tick rows the channel takes on.
        table: The per-tick semitone contour that moves the note.
        channel: The NES channel the slice was reconstructed for.
        initial_pitch: Pitch the slice's contour is measured against.
        ticks: How many ticks the instrument runs before it loops.
    """

    number: int
    instrument: BitphaseInstrument
    table: BitphaseTable
    channel: ChannelName
    initial_pitch: int
    ticks: int


VoiceTable = Dict[Tuple[str, ChannelName], Voice]


def _build_voice(
    index: int,
    name: str,
    channel: ChannelName,
    initial_pitch: int,
    envelopes: ChannelEnvelopes,
    *,
    maximum_table_id: int,
) -> Voice:
    """Numbers one channel slice and packages it as an instrument-and-table pair.

    Instruments and tables are numbered alike, so a pattern cell names the same position
    in both columns. The document states how far the table numbering reaches, since a song
    that carries a groove holds one table of its own above the slices.

    Raises:
        ValueError: If the position runs past what a pattern column can name, or past the
            table ids the document leaves to its slices.
    """
    number = index + MIN_INSTRUMENT_ID
    if number > MAX_INSTRUMENT_ID:
        raise ValueError(f"Document exceeds the Bitphase limit of {MAX_INSTRUMENT_ID} instruments")

    table_id = index + MIN_TABLE_ID
    if table_id > maximum_table_id:
        raise ValueError(f"Document holds room for {maximum_table_id + 1} slice tables")

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
        channel=channel,
        initial_pitch=initial_pitch,
        ticks=len(envelopes.rows),
    )


def _note_cell(channel_generator: ChannelName, pitch: int) -> NoteCell:
    """Resolves a pitch to the note column of the channel the row sits on.

    The noise channel reads its note as a period selector, so its pitch takes the
    mapping that reproduces that period; every other channel reads the tuning table.
    """
    if channel_generator == ChannelName.NOISE:
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
        channel = CHANNEL_TO_INDEX[voice.channel]
        note = _note_cell(voice.channel, voice.initial_pitch)
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

    Every channel slice becomes an instrument and the table that carries its pitch
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
            instrument.channel,
            instrument.features.initial_pitch,
            features_to_envelopes(
                instrument.features,
                instrument.channel,
                loop=instrument.loop,
            ),
            maximum_table_id=MAX_TABLE_ID,
        )
        for index, instrument in enumerate(request.instruments)
    ]

    length = _preview_length(voices)
    order = _preview_order(voices, length)
    patterns = _preview_patterns(voices, length, len(order))

    return BitphaseProject(
        name=request.name,
        author=NO_AUTHOR,
        songs=(
            _build_song(
                patterns,
                speed=PREVIEW_SPEED,
                nes_frequency=request.nes_frequency,
            ),
        ),
        pattern_order=order,
        tables=tuple(voice.table for voice in voices),
        instruments=tuple(voice.instrument for voice in voices),
    )


def instrument_to_bitphase(request: InstrumentExport) -> BitphaseProject:
    """Builds a playable Bitphase document holding one channel slice.

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


def _build_voice_table(
    project: Project,
    *,
    maximum_table_id: int,
) -> Tuple[List[Voice], VoiceTable]:
    voices: List[Voice] = []
    by_reference: VoiceTable = {}

    for sample_slice in iterate_sample_slices(project):
        envelopes = features_to_envelopes(
            sample_slice.features,
            sample_slice.channel,
            loop=sample_slice.sample.loop,
        )
        voice = _build_voice(
            sample_slice.index,
            sample_slice.instrument_name,
            sample_slice.channel,
            sample_slice.features.initial_pitch,
            envelopes,
            maximum_table_id=maximum_table_id,
        )
        voices.append(voice)
        by_reference[sample_slice.key] = voice

    return voices, by_reference


def _resolve_voice(reference: Instrument, voices: VoiceTable) -> Voice:
    voice = voices.get((reference.sample_id, reference.channel_name))
    if voice is None:
        raise ValueError(
            f"Row references sample '{reference.sample_id}' slice " f"'{reference.channel_name}' that has no instrument"
        )

    return voice


def _volume_column(volume: Optional[int]) -> int:
    """Writes a tracker line's volume column as the value Bitphase reads it as.

    Bitphase spends ``0`` on carrying the channel's level forward, so silence holds a value
    of its own: a line asking for volume ``0`` writes ``VOLUME_OFF`` and the channel falls
    silent from that line on, while a line naming a level writes it verbatim. Bitphase's own
    editor prints ``VOLUME_OFF`` as the digit ``0``, so this is the cell a user types there.
    """
    if volume is None:
        return NO_VOLUME_CHANGE

    if volume == SILENT_VOLUME:
        return VOLUME_OFF

    return volume


def _row_cell(
    row: Row,
    channel_generator: ChannelName,
    voices: VoiceTable,
) -> BitphaseRow:
    """Converts one tracker line to the Bitphase row that plays it.

    Raises:
        ValueError: If the line references a sample slice that has no instrument.
    """
    volume = _volume_column(row.volume)
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
    channel: ChannelName,
    voices: VoiceTable,
) -> List[BitphaseRow]:
    cells = [_row_cell(row, channel, voices) for row in rows[:length]]
    cells.extend(BitphaseRow() for _ in range(length - len(cells)))
    return cells


def _project_groove(project: Project) -> Groove:
    """Spreads the tempo a project states across the rows of one pattern.

    A Bitphase song holds a speed alone, so the fractional row rate a tempo asks for is
    carried by a groove: whole tick counts that vary from row to row and average out to the
    rate, placed by the metre so the longer rows fall on the bar and the beat. The engine's
    own speed range bounds them, and the groove's mean states the rate it reached.
    """
    settings = project.settings
    return calculate_groove(
        RowRate.from_settings(settings),
        Metre.from_settings(settings, rows=project.song.rows_per_pattern),
        minimum_ticks=MIN_INITIAL_SPEED,
        maximum_ticks=MAX_INITIAL_SPEED,
    )


def _maximum_slice_table_id(groove: Groove) -> int:
    """The last table id the document leaves to its slices.

    A groove whose rows differ occupies the table above the last slice, so the slices reach
    one id less far; a groove whose rows last alike is carried by the song's initial speed
    and leaves the whole column to them.
    """
    if groove.is_uniform:
        return MAX_TABLE_ID

    return MAX_TABLE_ID - GROOVE_TABLE_COUNT


def _groove_table(groove: Groove, table_id: int) -> BitphaseTable:
    """Writes the groove as the table a speed effect reads one entry per pattern row from."""
    return BitphaseTable(
        id=table_id,
        rows=groove.ticks,
        loop=LOOP_FROM_START,
        name=GROOVE_TABLE_NAME,
    )


def _speed_effect(table_id: int) -> EffectCell:
    """Names the table a row takes its own duration from.

    The parameter states a speed directly where an effect carries no table, so an effect
    that names one leaves it empty; the delay stays at zero, which is what Bitphase reads
    on a speed effect.
    """
    return EffectCell(
        effect=int(EffectId.SPEED),
        delay=SPEED_EFFECT_DELAY,
        parameter=NO_EFFECT_PARAMETER,
        table_index=table_id,
    )


def _groove_channel_rows(length: int, table_id: int) -> List[BitphaseRow]:
    """Rests a channel for a whole pattern beyond the groove trigger its first row carries.

    A speed effect applies from whichever channel holds it, so the groove rides the silent
    DPCM channel and leaves every sounding channel its own effect column. The table then
    advances one entry per row from where the trigger placed it, and triggering it again on
    each pattern's first row keeps every row on the entry that describes it.
    """
    rows = [BitphaseRow() for _ in range(length)]
    rows[GROOVE_TRIGGER_ROW] = BitphaseRow(effects=(_speed_effect(table_id),))
    return rows


def _document_tables(
    voices: Sequence[Voice],
    groove_table: Optional[BitphaseTable],
) -> Tuple[BitphaseTable, ...]:
    """Gathers the tables a document holds: one per slice, and the groove where it takes one."""
    tables = tuple(voice.table for voice in voices)
    if groove_table is None:
        return tables

    return tables + (groove_table,)


def _project_patterns(
    project: Project,
    voices: VoiceTable,
    groove_table: Optional[BitphaseTable],
) -> Tuple[BitphasePattern, ...]:
    """Flattens the song's per-channel arrangement into whole-pattern order positions.

    A SampleToNES order frame points every channel at its own pattern, where a Bitphase
    order position names one pattern that spans all channels, so each frame becomes a
    pattern of its own carrying that frame's channels side by side. Every pattern triggers
    the groove table it is given, so the tempo holds wherever the order jumps.
    """
    song = project.song
    length = song.rows_per_pattern
    patterns: List[BitphasePattern] = []

    for position, frame in enumerate(song.order):
        channel_rows = _empty_channels(length)
        if groove_table is not None:
            channel_rows[int(GROOVE_CHANNEL)] = _groove_channel_rows(
                length,
                groove_table.id,
            )

        for channel_name in ChannelName.items():
            index = frame.get(channel_name)
            if index is None:
                continue

            pattern = song.channels[channel_name].pattern(index)
            if pattern is None:
                continue

            channel_index = CHANNEL_TO_INDEX[channel_name]
            channel_rows[channel_index] = _channel_rows(
                pattern.rows,
                length,
                channel_name,
                voices,
            )

        patterns.append(_to_pattern(position, length, channel_rows))

    return tuple(patterns)


def project_to_bitphase(project: Project) -> BitphaseProject:
    """Maps a project's samples, song and tempo onto the Bitphase document IR.

    The song carries the project's tempo as a groove, which is the initial speed on its own
    where every row lasts alike and a table the patterns trigger where the rows differ.

    Args:
        project: The project to write.

    Returns:
        BitphaseProject: The document to serialize.

    Raises:
        ValueError: If the project holds more than Bitphase has room for, or a row
            references a sample slice that has no instrument.
    """
    groove = _project_groove(project)
    voices, by_reference = _build_voice_table(
        project,
        maximum_table_id=_maximum_slice_table_id(groove),
    )
    groove_table = (
        None
        if groove.is_uniform
        else _groove_table(
            groove,
            len(voices) + MIN_TABLE_ID,
        )
    )
    patterns = _project_patterns(project, by_reference, groove_table)
    settings = project.settings
    info = project.info

    return BitphaseProject(
        name=info.title,
        author=info.author,
        songs=(
            _build_song(
                patterns,
                speed=groove.ticks[GROOVE_TRIGGER_ROW],
                nes_frequency=settings.nes_frequency,
            ),
        ),
        pattern_order=tuple(pattern.id for pattern in patterns),
        tables=_document_tables(voices, groove_table),
        instruments=tuple(voice.instrument for voice in voices),
    )
