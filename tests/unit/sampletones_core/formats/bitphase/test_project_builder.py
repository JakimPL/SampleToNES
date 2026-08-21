from pathlib import Path
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import SILENT_VOLUME
from sampletones_core.formats.bitphase.builder import project_to_bitphase
from sampletones_core.formats.bitphase.model.pattern import BitphaseRow, EffectCell
from sampletones_core.formats.bitphase.model.project import BitphaseProject
from sampletones_core.formats.bitphase.notes import (
    note_index_to_note_cell,
    pitch_to_note_index,
)
from sampletones_core.formats.bitphase.specification.channels import ChannelIndex
from sampletones_core.formats.bitphase.specification.effects import (
    NO_EFFECT_PARAMETER,
    SPEED_EFFECT_DELAY,
    EffectId,
)
from sampletones_core.formats.bitphase.specification.instruments import LOOP_FROM_START
from sampletones_core.formats.bitphase.specification.patterns import (
    NO_INSTRUMENT_CHANGE,
    NO_TABLE_CHANGE,
    NO_VOLUME_CHANGE,
    SYMBOL_BASE,
    TABLE_COLUMN_OFFSET,
    VOLUME_OFF,
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
from tests.suite.stems import single_entry_stems_data

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
SILENCED_ROW: Final[int] = 7
GROOVE_TEMPO: Final[int] = 210
GROOVE_TICKS: Final[Tuple[int, ...]] = (5, 4, 4, 4, 5, 4, 4, 4)


def build_reconstruction(
    instructions: Mapping[ChannelName, Sequence[Instruction]],
) -> Reconstruction:
    approximations = {channel: np.zeros(RECONSTRUCTION_LENGTH, dtype=np.float32) for channel in instructions}
    return Reconstruction.create(
        approximation=np.zeros(RECONSTRUCTION_LENGTH, dtype=np.float32),
        approximations=approximations,
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=(Path("/dev/null"),),
        stems_data=single_entry_stems_data(list(Config().generation.channels), instructions),
    )


def pulse_sample(name: str, pitch: int) -> Sample:
    instructions = [PulseInstruction(on=True, pitch=pitch, volume=15, duty_cycle=0)]
    return Sample(
        name=name,
        reconstruction=build_reconstruction({ChannelName.PULSE1: instructions}),
    )


def triangle_sample(name: str, pitch: int) -> Sample:
    instructions = [TriangleInstruction(on=True, pitch=pitch)]
    return Sample(
        name=name,
        reconstruction=build_reconstruction({ChannelName.TRIANGLE: instructions}),
    )


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
        command=Instrument(sample_id=lead.id, channel_name=ChannelName.PULSE1),
        transpose=0,
        volume=ROW_VOLUME,
    )
    pulse_rows[NOTE_OFF_ROW] = Row(command=NoteOff())
    pulse_rows[TRANSPOSED_ROW] = Row(
        command=Instrument(sample_id=lead.id, channel_name=ChannelName.PULSE1),
        transpose=TRANSPOSE,
    )
    pulse_rows[SILENCED_ROW] = Row(volume=SILENT_VOLUME)

    triangle_rows: List[Row] = [Row() for _ in range(ROWS_PER_PATTERN)]
    triangle_rows[TRIGGER_ROW] = Row(
        command=Instrument(sample_id=bass.id, channel_name=ChannelName.TRIANGLE),
        transpose=0,
    )

    channels = {
        ChannelName.PULSE1: Channel(name=ChannelName.PULSE1, patterns={0: Pattern(rows=pulse_rows)}),
        ChannelName.PULSE2: Channel(name=ChannelName.PULSE2, patterns={}),
        ChannelName.TRIANGLE: Channel(name=ChannelName.TRIANGLE, patterns={0: Pattern(rows=triangle_rows)}),
        ChannelName.NOISE: Channel(name=ChannelName.NOISE, patterns={}),
    }
    order: List[Dict[ChannelName, Optional[int]]] = [
        {ChannelName.PULSE1: 0, ChannelName.TRIANGLE: 0},
        {ChannelName.PULSE1: None, ChannelName.TRIANGLE: 0},
    ]

    project = Project.create(title="Demo", author="Tester", settings=ProjectSettings())
    project.samples = samples
    project.song = Song(rows_per_pattern=ROWS_PER_PATTERN, order=order, channels=channels)
    return project


@pytest.fixture(name="document")
def document_fixture(source: Project) -> BitphaseProject:
    return project_to_bitphase(source)


@pytest.fixture(name="grooved_document")
def grooved_document_fixture(source: Project) -> BitphaseProject:
    """The same project at a tempo whose row rate falls between two whole tick counts."""
    source.settings.tempo = GROOVE_TEMPO
    return project_to_bitphase(source)


def groove_channel_rows(document: BitphaseProject, pattern_index: int) -> Tuple[BitphaseRow, ...]:
    """The lines of the channel the groove rides, within one pattern."""
    return document.songs[0].patterns[pattern_index].channels[int(ChannelIndex.DPCM)].rows


class TestTheDocumentCarriesTheProject:
    def test_the_title_and_author_cross_over(self, document: BitphaseProject, source: Project) -> None:
        assert (document.name, document.author) == (
            source.info.title,
            source.info.author,
        )

    def test_the_speed_and_tick_rate_cross_over(self, document: BitphaseProject, source: Project) -> None:
        song = document.songs[0]
        assert song.initial_speed == source.settings.speed
        assert song.interrupt_frequency == source.settings.nes_frequency

    def test_every_sample_slice_becomes_an_instrument(self, document: BitphaseProject) -> None:
        assert [instrument.name for instrument in document.instruments] == [
            "Lead (pulse1)",
            "Bass (triangle)",
        ]


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

    def test_a_row_asking_for_silence_silences_the_channel(self, document: BitphaseProject) -> None:
        """Bitphase reads a stored volume of ``0`` as "carry the level forward", so silence
        is the value below it — the one its editor prints as the digit ``0`` — and a row
        asking for silence has to reach a different column than a row asking for nothing.
        """
        rows = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows
        assert rows[SILENCED_ROW].volume == VOLUME_OFF
        assert rows[SILENCED_ROW].volume != rows[TRANSPOSED_ROW].volume

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


class TestTheTempoBecomesAGroove:
    """A Bitphase song holds one speed value per row, so the fractional row rate most tempi
    ask for is carried by a groove: whole tick counts that vary from row to row. The groove
    reaches the engine as a table a speed effect reads a row at a time, triggered from the
    channel this exporter leaves silent. A tempo whose rows all last alike is carried by the
    song's initial speed alone.
    """

    def test_a_tempo_the_speed_column_states_needs_no_table(self, document: BitphaseProject) -> None:
        assert len(document.tables) == len(document.instruments)

    def test_a_tempo_the_speed_column_states_leaves_the_groove_channel_resting(
        self,
        document: BitphaseProject,
    ) -> None:
        assert all(row == BitphaseRow() for row in groove_channel_rows(document, 0))

    def test_a_groove_takes_the_table_above_the_slices(self, grooved_document: BitphaseProject) -> None:
        table = grooved_document.tables[-1]
        assert table.id == len(grooved_document.instruments)
        assert table.loop == LOOP_FROM_START

    def test_the_table_holds_the_ticks_each_row_lasts(self, grooved_document: BitphaseProject) -> None:
        assert grooved_document.tables[-1].rows == GROOVE_TICKS

    def test_the_song_starts_on_the_ticks_its_first_row_lasts(self, grooved_document: BitphaseProject) -> None:
        assert grooved_document.songs[0].initial_speed == GROOVE_TICKS[TRIGGER_ROW]

    def test_every_pattern_triggers_the_groove_on_its_first_row(self, grooved_document: BitphaseProject) -> None:
        """The speed table advances one entry per row and returns to the entry the trigger
        names, so triggering it again at each pattern start holds every row on the entry that
        describes it however the order jumps.
        """
        trigger = EffectCell(
            effect=int(EffectId.SPEED),
            delay=SPEED_EFFECT_DELAY,
            parameter=NO_EFFECT_PARAMETER,
            table_index=grooved_document.tables[-1].id,
        )
        triggers = [
            groove_channel_rows(grooved_document, index)[TRIGGER_ROW].effects
            for index in range(len(grooved_document.songs[0].patterns))
        ]
        assert triggers == [(trigger,)] * len(triggers)

    def test_the_groove_channel_carries_nothing_but_the_trigger(self, grooved_document: BitphaseProject) -> None:
        rows = groove_channel_rows(grooved_document, 0)
        assert all(row == BitphaseRow() for row in rows[TRIGGER_ROW + 1 :])

    def test_the_sounding_channels_keep_their_effect_columns(self, grooved_document: BitphaseProject) -> None:
        """The groove rides the silent channel, so every channel that plays keeps the one
        effect column the chip gives it.
        """
        channels = grooved_document.songs[0].patterns[0].channels[: int(ChannelIndex.DPCM)]
        assert all(row.effects == (None,) for channel in channels for row in channel.rows)


class TestAnUnbuildableRow:
    def test_a_row_naming_a_slice_with_no_instrument_is_refused(self, source: Project, lead: Sample) -> None:
        rows: List[Row] = [Row() for _ in range(ROWS_PER_PATTERN)]
        rows[TRIGGER_ROW] = Row(command=Instrument(sample_id=lead.id, channel_name=ChannelName.PULSE2))
        source.song.channels[ChannelName.PULSE2] = Channel(
            name=ChannelName.PULSE2,
            patterns={0: Pattern(rows=rows)},
        )
        source.song.order[0][ChannelName.PULSE2] = 0

        with pytest.raises(ValueError, match="has no instrument"):
            project_to_bitphase(source)
