from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.rows.levels import cell_volume, full_level_notes
from sampletones_core.exporters.rows.pitch import highest_step, written_pitch
from sampletones_core.exporters.skipped import BuiltDocument, find_skipped_rows
from sampletones_core.exporters.slices import (
    InstrumentEntry,
    InstrumentSlot,
    InstrumentTable,
    iterate_instrument_entries,
)
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.module import (
    FamiTrackerModule,
    ModuleInformation,
    ModuleParameters,
    OrderFrame,
    Track,
)
from sampletones_core.formats.famitracker.model.pattern import PatternData, RowCell
from sampletones_core.formats.famitracker.notes import (
    period_to_note_cell,
    pitch_to_note_cell,
    resolve_machine,
)
from sampletones_core.formats.famitracker.sequences.features import (
    features_to_instrument_sequences,
    features_truncation,
)
from sampletones_core.formats.famitracker.specification.channels import (
    CHANNEL_COUNT_2A03,
    CHANNEL_TO_ID,
    ChannelId,
)
from sampletones_core.formats.famitracker.specification.instruments import (
    MAX_INSTRUMENTS,
)
from sampletones_core.formats.famitracker.specification.parameters import (
    DEFAULT_HIGHLIGHT_FIRST,
    DEFAULT_HIGHLIGHT_SECOND,
    DEFAULT_SPEED_SPLIT_POINT,
    DEFAULT_VIBRATO_STYLE,
    EXPANSION_NONE,
)
from sampletones_core.formats.famitracker.specification.patterns import (
    DEFAULT_EFFECT_COLUMNS,
    DPCM_EMPTY_PATTERN_INDEX,
    EMPTY_EFFECT,
    EMPTY_EFFECT_PARAM,
    EMPTY_INSTRUMENT,
    EMPTY_NOTE,
    EMPTY_VOLUME,
    MAX_FRAMES,
    MAX_PATTERN_INDEX,
    MIN_OCTAVE,
    NoteValue,
)
from sampletones_core.formats.famitracker.specification.sequences import SequenceKind
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_shared.application import SAMPLETONES_COPYRIGHT

PatternCell = Tuple[int, int]


@dataclass(frozen=True)
class RowTarget:
    """The instrument a row naming a voice on one channel triggers, with what places its note.

    Attributes:
        slot: The instrument's position in the module and the reference a row's transpose steps from.
        contour_top: The highest semitone step the instrument's arpeggio moves the note by.
    """

    slot: InstrumentSlot
    contour_top: int


RowTargets = Dict[Tuple[str, ChannelName], RowTarget]


def build_instrument(
    index: int,
    name: str,
    features: Features,
) -> Instrument2A03:
    """Builds one FamiTracker instrument from a set of envelopes.

    The envelopes become the instrument's five 2A03 sequences, so an instrument reaching a
    ``.fti`` file on its own and one taking a slot in a module are built the same way.

    Args:
        index: The slot the instrument is numbered under.
        name: The name FamiTracker lists the instrument by.
        features: The per-dimension envelopes the sequences are read from.

    Returns:
        The instrument the envelopes describe.
    """
    sequences = features_to_instrument_sequences(features)

    return Instrument2A03(
        index=index,
        name=name,
        sequences=sequences,
    )


def build_instrument_table(project: Project) -> Tuple[List[Instrument2A03], InstrumentTable]:
    """Builds the module's instruments and the table a pattern row resolves through.

    A sample contributes one instrument for every channel its reconstruction covers, so it yields
    one to four; a hand-written voice contributes one instrument every channel it sounds on
    reaches, each against that channel's own root. Instruments are numbered in voice order, then channel order.

    Raises:
        ValueError: If the project holds more instruments than FamiTracker has room for.
    """
    return _instrument_table(tuple(iterate_instrument_entries(project)))


def _instrument_table(entries: Sequence[InstrumentEntry]) -> Tuple[List[Instrument2A03], InstrumentTable]:
    """Builds the instruments the entries describe and the table a pattern row resolves through.

    Raises:
        ValueError: If the entries hold more instruments than FamiTracker has room for.
    """
    instruments: List[Instrument2A03] = []
    slots: InstrumentTable = {}

    for entry in entries:
        if entry.index >= MAX_INSTRUMENTS:
            raise ValueError(f"Module exceeds the FamiTracker limit of {MAX_INSTRUMENTS} instruments")

        instruments.append(
            build_instrument(
                entry.index,
                entry.name,
                entry.features,
            )
        )
        for channel, slot in entry.slots.items():
            slots[(entry.voice_id, channel)] = slot

    return instruments, slots


def _row_targets(
    instruments: Sequence[Instrument2A03],
    slots: InstrumentTable,
) -> RowTargets:
    """Pairs every slot a row resolves through with the highest step its instrument's arpeggio reaches.

    The arpeggio is read as the module stores it, so the step is one FamiTracker plays.
    """
    contour_tops = {
        instrument.index: highest_step(instrument.sequences[SequenceKind.ARPEGGIO].items) for instrument in instruments
    }
    return {
        key: RowTarget(
            slot=slot,
            contour_top=contour_tops[slot.index],
        )
        for key, slot in slots.items()
    }


def _note_and_octave(
    transpose: int,
    channel_generator: ChannelName,
    target: RowTarget,
) -> Tuple[int, int]:
    """Resolves an instrument moved by a row's transpose to the note column that triggers it.

    The noise channel reads its note as a period, wrapped into the sixteen it has. Every other
    channel reads the note its arpeggio moves, so the transposed pitch is written at the note that
    keeps the contour where the song plays it — see :func:`written_pitch`.
    """
    base_pitch = target.slot.initial_pitch + transpose
    if channel_generator == ChannelName.NOISE:
        cell = period_to_note_cell(base_pitch)
    else:
        cell = pitch_to_note_cell(written_pitch(base_pitch, target.contour_top))

    return cell.note, cell.octave


def _row_cell(
    row: Row,
    row_number: int,
    channel_generator: ChannelName,
    targets: RowTargets,
    *,
    full_level: bool,
) -> Optional[RowCell]:
    """Converts one tracker line to the cell that plays it, and ``None`` where the line is empty.

    A note-on naming a voice with no instrument on this channel plays nothing in the song, so it
    becomes the note cut that silences the channel. The volume column states what
    :func:`cell_volume` gives the row, which is the full level on a note FamiTracker would otherwise
    start at the level the channel carries.
    """
    note = EMPTY_NOTE
    octave = MIN_OCTAVE
    instrument = EMPTY_INSTRUMENT
    stated_volume = cell_volume(row, channel_generator, full_level=full_level)
    volume = stated_volume if stated_volume is not None else EMPTY_VOLUME

    match row.command:
        case NoteOff():
            note = int(NoteValue.HALT)
        case NoteOn() as reference:
            target = targets.get((reference.voice_id, channel_generator))
            if target is None:
                note = int(NoteValue.HALT)
            else:
                instrument = target.slot.index
                note, octave = _note_and_octave(
                    row.transpose or 0,
                    channel_generator,
                    target,
                )
        case None:
            pass

    effects = tuple((EMPTY_EFFECT, EMPTY_EFFECT_PARAM) for _ in range(DEFAULT_EFFECT_COLUMNS))
    cell = RowCell(
        row_number=row_number,
        note=note,
        octave=octave,
        instrument=instrument,
        volume=volume,
        effects=effects,
    )
    return cell if _has_data(cell) else None


def _has_data(cell: RowCell) -> bool:
    return (
        cell.note != EMPTY_NOTE
        or cell.instrument != EMPTY_INSTRUMENT
        or cell.volume != EMPTY_VOLUME
        or any(effect != EMPTY_EFFECT or param != EMPTY_EFFECT_PARAM for effect, param in cell.effects)
    )


def _full_level_cells(song: Song, channel_name: ChannelName) -> FrozenSet[PatternCell]:
    """The pattern cells of one channel that write the full level, by pattern index and row.

    A module stores a pattern once for every frame that plays it, so a cell writes the full level
    wherever any of those frames reaches its note carrying another, which FamiTracker plays as the
    frames come and again from the first once the order ends.
    """
    return frozenset((place.pattern_index, place.row_index) for place in full_level_notes(song, channel_name))


def _channel_patterns(
    name: ChannelName,
    channel: Channel,
    targets: RowTargets,
    full_level_cells: FrozenSet[PatternCell],
) -> List[PatternData]:
    """Converts one channel's pattern pool, writing the full level on the cells named."""
    channel_id = CHANNEL_TO_ID[name]
    patterns: List[PatternData] = []

    for index in sorted(channel.patterns):
        if index > MAX_PATTERN_INDEX:
            raise ValueError(f"Pattern index {index} exceeds the FamiTracker limit of {MAX_PATTERN_INDEX}")

        pattern = channel.patterns[index]
        rows = tuple(
            cell
            for cell in (
                _row_cell(
                    row,
                    row_number,
                    name,
                    targets,
                    full_level=(index, row_number) in full_level_cells,
                )
                for row_number, row in enumerate(pattern.rows)
            )
            if cell is not None
        )
        if rows:
            patterns.append(
                PatternData(
                    channel=channel_id,
                    index=index,
                    rows=rows,
                )
            )

    return patterns


def _reserved_empty_index(channel: Channel) -> int:
    if not channel.patterns:
        return DPCM_EMPTY_PATTERN_INDEX

    return max(channel.patterns) + 1


def _build_order(song: Song) -> Tuple[OrderFrame, ...]:
    if len(song.order) > MAX_FRAMES:
        raise ValueError(f"Order length {len(song.order)} exceeds the FamiTracker limit of {MAX_FRAMES} frames")

    empty_indices = {channel: _reserved_empty_index(song.channels[channel]) for channel in ChannelName.items()}
    for channel, empty_index in empty_indices.items():
        if empty_index > MAX_PATTERN_INDEX:
            raise ValueError(f"Channel '{channel}' has no free pattern index for empty order slots")

    frames: List[OrderFrame] = []
    for frame in song.order:
        entries: List[int] = []
        for channel in ChannelName.items():
            index = frame.get(channel)
            entries.append(index if index is not None else empty_indices[channel])

        entries.append(DPCM_EMPTY_PATTERN_INDEX)
        frames.append(tuple(entries))

    return tuple(frames)


def project_to_module(project: Project) -> FamiTrackerModule:
    """Maps a project's samples and song onto the FamiTracker module IR."""
    return build_module(project).document


def build_module(project: Project) -> BuiltDocument[FamiTrackerModule]:
    """Maps a project onto the FamiTracker module IR and lists what it had to leave out.

    A row naming a voice on a channel the voice has no instrument for plays nothing in the song,
    so the module holds a note cut there and the row is listed beside it. A dimension longer than a
    sequence holds keeps its opening items, and the instruments shortened that way are reported
    beside the rows. The rows write their notes and levels so FamiTracker plays them where the
    song's own walk does.

    Raises:
        ValueError: If the project holds more than FamiTracker has room for.
    """
    entries = tuple(iterate_instrument_entries(project))
    instruments, slots = _instrument_table(entries)
    song = project.song
    settings = project.settings
    info = project.info

    machine, engine_speed = resolve_machine(settings.nes_frequency)
    parameters = ModuleParameters(
        expansion_chip=EXPANSION_NONE,
        channel_count=CHANNEL_COUNT_2A03,
        machine=machine,
        engine_speed=engine_speed,
        vibrato_style=DEFAULT_VIBRATO_STYLE,
        highlight_first=DEFAULT_HIGHLIGHT_FIRST,
        highlight_second=DEFAULT_HIGHLIGHT_SECOND,
        speed_split_point=DEFAULT_SPEED_SPLIT_POINT,
    )
    information = ModuleInformation(
        title=info.title,
        author=info.author,
        copyright=SAMPLETONES_COPYRIGHT,
    )

    targets = _row_targets(instruments, slots)
    patterns: List[PatternData] = []
    for channel in ChannelName.items():
        patterns.extend(
            _channel_patterns(
                channel,
                song.channels[channel],
                targets,
                _full_level_cells(song, channel),
            ),
        )

    track = Track(
        title=info.title,
        speed=settings.speed,
        tempo=settings.tempo,
        rows_per_pattern=song.rows_per_pattern,
        order=_build_order(song),
        patterns=tuple(patterns),
        effect_columns={channel_id: DEFAULT_EFFECT_COLUMNS for channel_id in ChannelId},
    )

    return BuiltDocument(
        document=FamiTrackerModule(
            parameters=parameters,
            information=information,
            instruments=tuple(instruments),
            track=track,
            comment=info.comment,
        ),
        skipped_rows=find_skipped_rows(song, slots),
        truncation=EnvelopeTruncation.summarize([features_truncation(entry.features) for entry in entries]),
    )
