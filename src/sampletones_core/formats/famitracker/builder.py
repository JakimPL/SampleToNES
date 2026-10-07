from typing import Final, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.rows.levels import cell_volume, full_level_notes
from sampletones_core.exporters.rows.transpose import PatternCell, PitchWalk, unreached_start
from sampletones_core.exporters.skipped import BuiltDocument, find_skipped_rows, in_song_order
from sampletones_core.exporters.slices import (
    InstrumentEntry,
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
from sampletones_core.formats.famitracker.notes import resolve_machine
from sampletones_core.formats.famitracker.sequences.features import (
    features_to_instrument_sequences,
    features_truncation,
)
from sampletones_core.formats.famitracker.slides import SlidePlan, slide_effect
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
from sampletones_core.formats.famitracker.targets import RowTargets, row_targets
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.voice import VoiceLookup
from sampletones_shared.application import SAMPLETONES_COPYRIGHT

NO_REPITCHED_INSTRUMENTS: Final[FrozenSet[int]] = frozenset()


def build_instrument(
    index: int,
    name: str,
    features: Features,
    *,
    repitched: bool,
) -> Instrument2A03:
    """Builds one FamiTracker instrument from a set of envelopes.

    The envelopes become the instrument's five 2A03 sequences, so an instrument reaching a
    ``.fti`` file on its own and one taking a slot in a module are built the same way.

    Args:
        index: The slot the instrument is numbered under.
        name: The name FamiTracker lists the instrument by.
        features: The per-dimension envelopes the sequences are read from.
        repitched: Whether a transpose row's note slide reaches the instrument in a module.

    Returns:
        The instrument the envelopes describe.
    """
    sequences = features_to_instrument_sequences(features, repitched=repitched)

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
    return _instrument_table(tuple(iterate_instrument_entries(project)), NO_REPITCHED_INSTRUMENTS)


def _instrument_table(
    entries: Sequence[InstrumentEntry],
    repitched: FrozenSet[int],
) -> Tuple[List[Instrument2A03], InstrumentTable]:
    """Builds the instruments the entries describe and the table a pattern row resolves through.

    Args:
        entries: The instruments to build, in the order the module numbers them.
        repitched: The instruments a transpose row's note slide reaches.

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
                repitched=entry.index in repitched,
            )
        )
        for channel, slot in entry.slots.items():
            slots[(entry.voice_id, channel)] = slot

    return instruments, slots


def _row_cell(
    row: Row,
    row_number: int,
    channel_generator: ChannelName,
    targets: RowTargets,
    slide: Optional[int],
    start: Optional[int],
    *,
    full_level: bool,
) -> Optional[RowCell]:
    """Converts one tracker line to the cell that plays it, and ``None`` where the line is empty.

    A note-on naming a voice with no instrument on this channel plays nothing in the song, so it
    becomes the note cut that silences the channel. A note-on starts the voice at the step ``start``
    the song's walk gave it, so an instrument placed without a pitch writes the note the channel was
    sounding, which FamiTracker would otherwise leave standing; a note-on that started nothing
    writes an empty note. The volume column states what :func:`cell_volume` gives the row, which is
    the full level on a note FamiTracker would otherwise start at the level the channel carries. A
    pitch row moving the note sounding writes the note slide ``slide`` names — see :class:`SlidePlan`.
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
            elif start is not None:
                instrument = target.slot.index
                cell_note = target.note_cell(start, channel_generator)
                note, octave = cell_note.note, cell_note.octave
        case None:
            pass

    effects = tuple((EMPTY_EFFECT, EMPTY_EFFECT_PARAM) for _ in range(DEFAULT_EFFECT_COLUMNS))
    if slide is not None:
        effects = (slide_effect(slide),) + effects[1:]
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
    slides: Mapping[PatternCell, int],
    starts: Mapping[PatternCell, Optional[int]],
    voices: VoiceLookup,
) -> List[PatternData]:
    """Converts one channel's pattern pool, writing the full level, the note slides and the starts on the cells named.

    A cell the order never reaches starts its note as the song would from silence.
    """
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
                    slides.get((index, row_number)),
                    starts.get((index, row_number), unreached_start(row, name, voices)),
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
    song's own walk does. A row moving the transpose of a note already sounding writes a note slide,
    and a row the module has no slide for is listed beside the others — see :class:`SlidePlan`.

    Raises:
        ValueError: If the project holds more than FamiTracker has room for.
    """
    entries = tuple(iterate_instrument_entries(project))
    song = project.song
    plain_instruments, slots = _instrument_table(entries, NO_REPITCHED_INSTRUMENTS)
    targets = row_targets(plain_instruments, slots)
    walks = {channel: PitchWalk.walk(song, channel, targets, project.voice) for channel in ChannelName.items()}
    slides = SlidePlan.build(walks, targets)
    instruments, _ = _instrument_table(entries, slides.repitched)
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

    patterns: List[PatternData] = []
    for channel in ChannelName.items():
        patterns.extend(
            _channel_patterns(
                channel,
                song.channels[channel],
                targets,
                _full_level_cells(song, channel),
                slides.slides[channel],
                walks[channel].pattern_starts(),
                project.voice,
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
        skipped_rows=in_song_order(find_skipped_rows(song, slots) + slides.skipped_rows),
        truncation=EnvelopeTruncation.summarize([features_truncation(entry.features) for entry in entries]),
    )
