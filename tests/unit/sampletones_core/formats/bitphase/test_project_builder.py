from pathlib import Path
from typing import Dict, Final, List, Mapping, Optional, Sequence

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.formats.bitphase.builder import project_to_bitphase
from sampletones_core.formats.bitphase.model.project import BitphaseProject
from sampletones_core.formats.bitphase.notes import note_index_to_note_cell, pitch_to_note_index
from sampletones_core.formats.bitphase.specification.channels import ChannelIndex
from sampletones_core.formats.bitphase.specification.patterns import (
    NO_INSTRUMENT_CHANGE,
    NO_TABLE_CHANGE,
    NO_VOLUME_CHANGE,
    SYMBOL_BASE,
    TABLE_COLUMN_OFFSET,
    NoteName,
)
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.instructions.implementation.triangle import TriangleInstruction
from sampletones_core.instructions.instruction import Instruction
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.song import Song
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures import IdentifiedCollection

RECONSTRUCTION_LENGTH: Final[int] = 4
ROWS_PER_PATTERN: Final[int] = 8
LEAD_PITCH: Final[int] = 60
BASS_PITCH: Final[int] = 36
TRANSPOSE: Final[int] = 5
ROW_VOLUME: Final[int] = 10
TRIGGER_ROW: Final[int] = 0
NOTE_OFF_ROW: Final[int] = 2
TRANSPOSED_ROW: Final[int] = 4
EMPTY_ROW: Final[int] = 6


def build_reconstruction(instructions: Mapping[GeneratorName, Sequence[Instruction]]) -> Reconstruction:
    approximations = {generator: np.zeros(RECONSTRUCTION_LENGTH, dtype=np.float32) for generator in instructions}
    return Reconstruction.create(
        approximation=np.zeros(RECONSTRUCTION_LENGTH, dtype=np.float32),
        approximations=approximations,
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


def pulse_sample(name: str, pitch: int) -> Sample:
    instructions = [PulseInstruction(on=True, pitch=pitch, volume=15, duty_cycle=0)]
    return Sample(name=name, reconstruction=build_reconstruction({GeneratorName.PULSE1: instructions}))


def triangle_sample(name: str, pitch: int) -> Sample:
    instructions = [TriangleInstruction(on=True, pitch=pitch)]
    return Sample(name=name, reconstruction=build_reconstruction({GeneratorName.TRIANGLE: instructions}))


@pytest.fixture(name="lead")
def lead_fixture() -> Sample:
    return pulse_sample("Lead", LEAD_PITCH)


@pytest.fixture(name="bass")
def bass_fixture() -> Sample:
    return triangle_sample("Bass", BASS_PITCH)


@pytest.fixture(name="source")
def source_fixture(lead: Sample, bass: Sample) -> Project:
    samples: IdentifiedCollection[Sample] = IdentifiedCollection()
    for sample in (lead, bass):
        samples.append(sample)

    pulse_rows: List[Row] = [Row() for _ in range(ROWS_PER_PATTERN)]
    pulse_rows[TRIGGER_ROW] = Row(
        command=Instrument(sample_id=lead.id, generator_name=GeneratorName.PULSE1),
        transpose=0,
        volume=ROW_VOLUME,
    )
    pulse_rows[NOTE_OFF_ROW] = Row(command=NoteOff())
    pulse_rows[TRANSPOSED_ROW] = Row(
        command=Instrument(sample_id=lead.id, generator_name=GeneratorName.PULSE1),
        transpose=TRANSPOSE,
    )

    triangle_rows: List[Row] = [Row() for _ in range(ROWS_PER_PATTERN)]
    triangle_rows[TRIGGER_ROW] = Row(
        command=Instrument(sample_id=bass.id, generator_name=GeneratorName.TRIANGLE),
        transpose=0,
    )

    channels = {
        GeneratorName.PULSE1: Channel(generator=GeneratorName.PULSE1, patterns={0: Pattern(rows=pulse_rows)}),
        GeneratorName.PULSE2: Channel(generator=GeneratorName.PULSE2, patterns={}),
        GeneratorName.TRIANGLE: Channel(generator=GeneratorName.TRIANGLE, patterns={0: Pattern(rows=triangle_rows)}),
        GeneratorName.NOISE: Channel(generator=GeneratorName.NOISE, patterns={}),
    }
    order: List[Dict[GeneratorName, Optional[int]]] = [
        {GeneratorName.PULSE1: 0, GeneratorName.TRIANGLE: 0},
        {GeneratorName.PULSE1: None, GeneratorName.TRIANGLE: 0},
    ]

    project = Project.create(title="Demo", author="Tester", settings=ProjectSettings())
    project.samples = samples
    project.song = Song(rows_per_pattern=ROWS_PER_PATTERN, order=order, channels=channels)
    return project


@pytest.fixture(name="document")
def document_fixture(source: Project) -> BitphaseProject:
    return project_to_bitphase(source)


class TestTheDocumentCarriesTheProject:
    def test_the_title_and_author_cross_over(self, document: BitphaseProject, source: Project) -> None:
        assert (document.name, document.author) == (source.info.title, source.info.author)

    def test_the_speed_and_tick_rate_cross_over(self, document: BitphaseProject, source: Project) -> None:
        song = document.songs[0]
        assert song.initial_speed == source.settings.speed
        assert song.interrupt_frequency == source.settings.nes_frequency

    def test_every_sample_slice_becomes_an_instrument(self, document: BitphaseProject) -> None:
        assert [instrument.name for instrument in document.instruments] == ["Lead (pulse1)", "Bass (triangle)"]


class TestTheOrderFlattens:
    """A SampleToNES order frame points each channel at its own pattern, where a Bitphase
    order position names one pattern spanning every channel, so each frame becomes a
    pattern of its own carrying that frame's channels side by side.
    """

    def test_each_order_frame_becomes_one_pattern(self, document: BitphaseProject, source: Project) -> None:
        assert len(document.songs[0].patterns) == len(source.song.order)

    def test_the_order_plays_those_patterns_in_turn(self, document: BitphaseProject, source: Project) -> None:
        assert document.pattern_order == tuple(range(len(source.song.order)))

    def test_a_frame_carries_the_channels_it_names(self, document: BitphaseProject) -> None:
        pattern = document.songs[0].patterns[0]
        triggered = {
            index
            for index, channel in enumerate(pattern.channels)
            if any(row.instrument != NO_INSTRUMENT_CHANGE for row in channel.rows)
        }
        assert triggered == {int(ChannelIndex.SQUARE1), int(ChannelIndex.TRIANGLE)}

    def test_a_channel_the_frame_leaves_unset_stays_empty(self, document: BitphaseProject) -> None:
        pattern = document.songs[0].patterns[1]
        rows = pattern.channels[int(ChannelIndex.SQUARE1)].rows
        assert all(row.instrument == NO_INSTRUMENT_CHANGE for row in rows)

    def test_every_pattern_is_as_long_as_the_song_declares(self, document: BitphaseProject, source: Project) -> None:
        patterns = document.songs[0].patterns
        assert all(pattern.length == source.song.rows_per_pattern for pattern in patterns)


class TestRowCells:
    def test_a_trigger_names_its_instrument_and_table(self, document: BitphaseProject) -> None:
        """Bitphase matches the instrument column against ``parseInt(id, 36)``, so the
        column and the instrument's own identifier name the same voice.
        """
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRIGGER_ROW]
        assert row.instrument == int(document.instruments[0].id, SYMBOL_BASE)
        assert row.table == document.tables[0].id + TABLE_COLUMN_OFFSET

    def test_a_trigger_plays_the_pitch_the_slice_was_reconstructed_at(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRIGGER_ROW]
        assert row.note == note_index_to_note_cell(pitch_to_note_index(LEAD_PITCH))

    def test_a_transposed_trigger_moves_that_pitch(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRANSPOSED_ROW]
        assert row.note == note_index_to_note_cell(pitch_to_note_index(LEAD_PITCH + TRANSPOSE))

    def test_a_row_volume_reaches_the_volume_column(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRIGGER_ROW]
        assert row.volume == ROW_VOLUME

    def test_a_row_that_sets_no_volume_leaves_the_column_alone(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRANSPOSED_ROW]
        assert row.volume == NO_VOLUME_CHANGE

    def test_a_note_off_stops_the_channel(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[NOTE_OFF_ROW]
        assert row.note.name == int(NoteName.OFF)
        assert row.instrument == NO_INSTRUMENT_CHANGE

    def test_a_blank_line_leaves_every_column_alone(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[EMPTY_ROW]
        assert row.note.name == int(NoteName.NONE)
        assert (row.instrument, row.table, row.volume) == (
            NO_INSTRUMENT_CHANGE,
            NO_TABLE_CHANGE,
            NO_VOLUME_CHANGE,
        )


class TestAnUnbuildableRow:
    def test_a_row_naming_a_slice_with_no_instrument_is_refused(self, source: Project, lead: Sample) -> None:
        rows: List[Row] = [Row() for _ in range(ROWS_PER_PATTERN)]
        rows[TRIGGER_ROW] = Row(command=Instrument(sample_id=lead.id, generator_name=GeneratorName.PULSE2))
        source.song.channels[GeneratorName.PULSE2] = Channel(
            generator=GeneratorName.PULSE2,
            patterns={0: Pattern(rows=rows)},
        )
        source.song.order[0][GeneratorName.PULSE2] = 0

        with pytest.raises(ValueError, match="has no instrument"):
            project_to_bitphase(source)
