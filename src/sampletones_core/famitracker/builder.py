from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.famitracker.model.instrument import Instrument2A03
from sampletones_core.famitracker.model.module import (
    FamiTrackerModule,
    ModuleInformation,
    ModuleParameters,
    OrderFrame,
    Track,
)
from sampletones_core.famitracker.model.pattern import PatternData, RowCell
from sampletones_core.famitracker.notes import (
    period_to_note_cell,
    pitch_to_note_cell,
    resolve_machine,
)
from sampletones_core.famitracker.sequences import features_to_instrument_sequences
from sampletones_core.famitracker.specification.channels import (
    CHANNEL_COUNT_2A03,
    GENERATOR_NAME_TO_CHANNEL_ID,
    ChannelId,
)
from sampletones_core.famitracker.specification.instruments import MAX_INSTRUMENTS
from sampletones_core.famitracker.specification.parameters import (
    DEFAULT_COPYRIGHT,
    DEFAULT_HIGHLIGHT_FIRST,
    DEFAULT_HIGHLIGHT_SECOND,
    DEFAULT_VIBRATO_STYLE,
    EXPANSION_NONE,
)
from sampletones_core.famitracker.specification.patterns import (
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
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.song import Song


@dataclass(frozen=True)
class InstrumentSlot:
    """Where a sample's generator slice landed in the instrument table."""

    index: int
    initial_pitch: int


InstrumentTable = Dict[Tuple[str, GeneratorName], InstrumentSlot]


def build_instrument_table(project: Project) -> Tuple[List[Instrument2A03], InstrumentTable]:
    """Builds one FamiTracker instrument per generator slice of every sample.

    Each sample contributes one instrument for every channel its reconstruction
    covers, so a sample yields one to four instruments. Instruments are numbered in
    sample order, then channel order.
    """
    instruments: List[Instrument2A03] = []
    slots: InstrumentTable = {}

    for sample in project.samples:
        features_by_generator = sample.reconstruction.export()
        for generator in GeneratorName.items():
            features = features_by_generator.get(generator)
            if features is None:
                continue

            index = len(instruments)
            if index >= MAX_INSTRUMENTS:
                raise ValueError(f"Module exceeds the FamiTracker limit of {MAX_INSTRUMENTS} instruments")

            sequences = features_to_instrument_sequences(
                volume=features.volume,
                arpeggio=features.arpeggio,
                pitch=features.pitch,
                hi_pitch=features.hi_pitch,
                duty_cycle=features.duty_cycle,
                loop=sample.loop,
            )
            name = f"{sample.name} {generator.capitalized}"
            instruments.append(Instrument2A03(index=index, name=name, sequences=sequences))
            slots[(sample.id, generator)] = InstrumentSlot(index=index, initial_pitch=features.initial_pitch)

    return instruments, slots


def _note_and_octave(
    command: Instrument,
    transpose: int,
    channel_generator: GeneratorName,
    slot: InstrumentSlot,
) -> Tuple[int, int]:
    base_pitch = slot.initial_pitch + transpose
    if channel_generator == GeneratorName.NOISE:
        cell = period_to_note_cell(base_pitch)
    else:
        cell = pitch_to_note_cell(base_pitch)
    return cell.note, cell.octave


def _row_cell(
    row: Row,
    row_number: int,
    channel_generator: GeneratorName,
    slots: InstrumentTable,
) -> Optional[RowCell]:
    note = EMPTY_NOTE
    octave = MIN_OCTAVE
    instrument = EMPTY_INSTRUMENT
    volume = row.volume if row.volume is not None else EMPTY_VOLUME

    match row.command:
        case NoteOff():
            note = int(NoteValue.HALT)
        case Instrument() as reference:
            slot = slots.get((reference.sample_id, reference.generator_name))
            if slot is None:
                raise ValueError(
                    f"Row references sample '{reference.sample_id}' slice "
                    f"'{reference.generator_name}' that has no instrument"
                )
            instrument = slot.index
            note, octave = _note_and_octave(reference, row.transpose or 0, channel_generator, slot)
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


def _channel_patterns(generator: GeneratorName, channel: Channel, slots: InstrumentTable) -> List[PatternData]:
    channel_id = GENERATOR_NAME_TO_CHANNEL_ID[generator]
    patterns: List[PatternData] = []

    for index in sorted(channel.patterns):
        if index > MAX_PATTERN_INDEX:
            raise ValueError(f"Pattern index {index} exceeds the FamiTracker limit of {MAX_PATTERN_INDEX}")

        pattern = channel.patterns[index]
        rows = tuple(
            cell
            for cell in (_row_cell(row, row_number, generator, slots) for row_number, row in enumerate(pattern.rows))
            if cell is not None
        )
        if rows:
            patterns.append(PatternData(channel=channel_id, index=index, rows=rows))

    return patterns


def _reserved_empty_index(channel: Channel) -> int:
    if not channel.patterns:
        return DPCM_EMPTY_PATTERN_INDEX
    return max(channel.patterns) + 1


def _build_order(song: Song) -> Tuple[OrderFrame, ...]:
    if len(song.order) > MAX_FRAMES:
        raise ValueError(f"Order length {len(song.order)} exceeds the FamiTracker limit of {MAX_FRAMES} frames")

    empty_indices = {generator: _reserved_empty_index(song.channels[generator]) for generator in GeneratorName.items()}
    for generator, empty_index in empty_indices.items():
        if empty_index > MAX_PATTERN_INDEX:
            raise ValueError(f"Channel '{generator}' has no free pattern index for empty order slots")

    frames: List[OrderFrame] = []
    for frame in song.order:
        entries: List[int] = []
        for generator in GeneratorName.items():
            index = frame.get(generator)
            entries.append(index if index is not None else empty_indices[generator])
        entries.append(DPCM_EMPTY_PATTERN_INDEX)
        frames.append(tuple(entries))

    return tuple(frames)


def project_to_module(project: Project) -> FamiTrackerModule:
    """Maps a project's samples and song onto the FamiTracker module IR."""
    instruments, slots = build_instrument_table(project)
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
    )
    information = ModuleInformation(title=info.title, author=info.author, copyright=DEFAULT_COPYRIGHT)

    patterns: List[PatternData] = []
    for generator in GeneratorName.items():
        patterns.extend(_channel_patterns(generator, song.channels[generator], slots))

    track = Track(
        title=info.title,
        speed=settings.speed,
        tempo=settings.tempo,
        rows_per_pattern=song.rows_per_pattern,
        order=_build_order(song),
        patterns=tuple(patterns),
        effect_columns={channel_id: DEFAULT_EFFECT_COLUMNS for channel_id in ChannelId},
    )

    return FamiTrackerModule(
        parameters=parameters,
        information=information,
        instruments=tuple(instruments),
        track=track,
        comment=info.comment,
    )
