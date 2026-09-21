from pathlib import Path
from typing import Final, List

import pytest

from sampletones_core.formats.bitphase.btp import write_btp
from sampletones_core.formats.bitphase.builder import project_to_bitphase
from sampletones_core.formats.bitphase.specification.channels import (
    CHANNEL_COUNT,
    CHANNEL_LABELS,
    ChannelIndex,
)
from sampletones_core.formats.bitphase.specification.chip import (
    CHIP_TYPE_NES,
    CPU_FREQUENCIES,
    MAX_INITIAL_SPEED,
    MAX_TUNING_PERIOD,
    MIN_INITIAL_SPEED,
    MIN_TUNING_PERIOD,
    TUNING_TABLE_LENGTH,
    ChipVariant,
)
from sampletones_core.formats.bitphase.specification.effects import (
    NO_EFFECT_PARAMETER,
    SPEED_EFFECT_DELAY,
    EffectId,
)
from sampletones_core.formats.bitphase.specification.instruments import (
    MAX_PULSE_WIDTH,
    MAX_VOLUME_OR_RATE,
    MIN_PULSE_WIDTH,
    MIN_VOLUME_OR_RATE,
    SILENT_VOLUME,
)
from sampletones_core.formats.bitphase.specification.macros import (
    MAX_MACRO_LENGTH,
    MIN_MACRO_LENGTH,
    NesMacroField,
)
from sampletones_core.formats.bitphase.specification.patterns import (
    FIRST_OCTAVE,
    FULL_VOLUME,
    MAX_NOTE_INDEX,
    MIN_NOTE_INDEX,
    NO_INSTRUMENT_CHANGE,
    NOTE_RANGE,
    TABLE_COLUMN_OFFSET,
    VOLUME_OFF,
    NoteName,
)
from sampletones_core.project.project import Project
from sampletones_core.timing import Meter, RowRate, calculate_groove
from sampletones_tools.samples.bitphase import GROOVE_TEMPO, at_tempo
from tests.suite.bitphase import (
    BITPHASE_NO_EFFECTS,
    LoadedEffect,
    LoadedNote,
    LoadedProject,
    LoadedRow,
    LoadedTable,
    parse_btp,
)

EXPECTED_INSTRUMENT_COUNT: Final[int] = 5
PLAYED_CHANNELS: Final[List[int]] = [
    int(ChannelIndex.SQUARE1),
    int(ChannelIndex.SQUARE2),
    int(ChannelIndex.TRIANGLE),
    int(ChannelIndex.NOISE),
]


def every_row(document: LoadedProject) -> List[LoadedRow]:
    """Every tracker line the document holds, across its patterns and their channels."""
    return [row for pattern in document.songs[0].patterns for channel in pattern.channels for row in channel.rows]


def note_index(note: LoadedNote) -> int:
    """The tuning-table index Bitphase's pattern processor reads back from a note cell."""
    return note.name - int(NoteName.C) + (note.octave - FIRST_OCTAVE) * NOTE_RANGE


@pytest.fixture
def groove_document(integration_project: Project, groove_document_path: Path) -> LoadedProject:
    project = at_tempo(integration_project, GROOVE_TEMPO)
    write_btp(groove_document_path, project_to_bitphase(project))
    return parse_btp(groove_document_path.read_bytes(), list(CHANNEL_LABELS))


class TestBtpPipeline:
    """End-to-end: synthesized + reconstructed samples -> Project -> `.btp` -> load."""

    def test_writes_a_loadable_document(self, integration_project: Project, document_path: Path) -> None:
        write_btp(document_path, project_to_bitphase(integration_project))
        assert document_path.exists()
        assert parse_btp(document_path.read_bytes(), list(CHANNEL_LABELS)).songs

    def test_the_document_carries_the_project_metadata(
        self,
        document: LoadedProject,
        integration_project: Project,
    ) -> None:
        assert document.name == integration_project.info.title
        assert document.author == integration_project.info.author

    def test_instrument_count_covers_every_slice(self, document: LoadedProject) -> None:
        assert len(document.instruments) == EXPECTED_INSTRUMENT_COUNT

    def test_every_instrument_carries_a_table(self, document: LoadedProject) -> None:
        assert len(document.tables) == len(document.instruments)

    def test_the_order_covers_the_song(self, document: LoadedProject, integration_project: Project) -> None:
        assert document.pattern_order == list(range(len(integration_project.song.order)))

    def test_the_order_names_patterns_the_song_holds(self, document: LoadedProject) -> None:
        held = {pattern.id for pattern in document.songs[0].patterns}
        assert set(document.pattern_order) <= held

    def test_patterns_cover_the_played_channels(self, document: LoadedProject) -> None:
        triggered = {
            index
            for pattern in document.songs[0].patterns
            for index, channel in enumerate(pattern.channels)
            if any(row.instrument != NO_INSTRUMENT_CHANGE for row in channel.rows)
        }
        assert triggered == set(PLAYED_CHANNELS)

    def test_the_document_carries_audible_volume(self, document: LoadedProject) -> None:
        assert any(
            value > SILENT_VOLUME
            for instrument in document.instruments
            for value in instrument.macro(NesMacroField.VOLUME_OR_RATE).values
        )


class TestTheLoaderReadsWhatWasWritten:
    """Bitphase reconstructs a project field by field, falling back to a default for each
    one it misses, so a field left out of the document reaches playback as that default.
    Reading the file back through the same fallbacks is the contract with the tracker.
    """

    def test_the_song_names_the_chip_it_drives(self, document: LoadedProject) -> None:
        assert document.songs[0].chip_type == CHIP_TYPE_NES

    def test_every_instrument_names_the_chip_whose_fields_it_holds(self, document: LoadedProject) -> None:
        assert {instrument.chip_type for instrument in document.instruments} == {CHIP_TYPE_NES}

    def test_the_song_carries_the_clock_its_tuning_was_built_from(self, document: LoadedProject) -> None:
        song = document.songs[0]
        assert song.chip_variant == ChipVariant.NTSC
        assert song.chip_frequency == CPU_FREQUENCIES[ChipVariant.NTSC]

    def test_the_song_carries_the_speed_and_tick_rate(
        self,
        document: LoadedProject,
        integration_project: Project,
    ) -> None:
        song = document.songs[0]
        assert song.initial_speed == integration_project.settings.speed
        assert song.interrupt_frequency == integration_project.settings.nes_frequency

    def test_the_tuning_table_covers_every_note_index(self, document: LoadedProject) -> None:
        table = document.songs[0].tuning_table
        assert len(table) == TUNING_TABLE_LENGTH
        assert all(MIN_TUNING_PERIOD <= period <= MAX_TUNING_PERIOD for period in table)

    def test_every_pattern_spans_the_chip_channels(self, document: LoadedProject) -> None:
        assert all(len(pattern.channels) == CHANNEL_COUNT for pattern in document.songs[0].patterns)

    def test_every_channel_fills_its_pattern(self, document: LoadedProject) -> None:
        assert all(
            len(channel.rows) == pattern.length
            for pattern in document.songs[0].patterns
            for channel in pattern.channels
        )

    def test_each_channel_is_labeled_as_its_position_names_it(self, document: LoadedProject) -> None:
        pattern = document.songs[0].patterns[0]
        assert [channel.label for channel in pattern.channels] == list(CHANNEL_LABELS)


class TestTheTriggersReachTheirVoices:
    """A trigger reaches playback through three columns at once — the instrument that
    shapes the note, the table that moves it, and the note itself — so a document whose
    columns disagree plays a different voice than the project arranged.
    """

    @pytest.fixture(name="triggers")
    def triggers_fixture(self, document: LoadedProject) -> List[LoadedRow]:
        return [row for row in every_row(document) if row.instrument != NO_INSTRUMENT_CHANGE]

    def test_the_song_triggers_its_instruments(self, triggers: List[LoadedRow]) -> None:
        assert triggers

    def test_every_trigger_names_an_instrument_the_document_holds(
        self,
        document: LoadedProject,
        triggers: List[LoadedRow],
    ) -> None:
        numbers = {instrument.number for instrument in document.instruments}
        assert {row.instrument for row in triggers} <= numbers

    def test_every_trigger_attaches_a_table_the_document_holds(
        self,
        document: LoadedProject,
        triggers: List[LoadedRow],
    ) -> None:
        columns = {table.id + TABLE_COLUMN_OFFSET for table in document.tables}
        assert {row.table for row in triggers} <= columns

    def test_every_trigger_names_a_pitched_note(self, triggers: List[LoadedRow]) -> None:
        assert all(int(NoteName.C) <= row.note.name <= int(NoteName.B) for row in triggers)

    def test_every_note_lands_inside_the_tuning_table(self, triggers: List[LoadedRow]) -> None:
        indices = [note_index(row.note) for row in triggers]
        assert all(MIN_NOTE_INDEX <= index <= MAX_NOTE_INDEX for index in indices)

    def test_every_volume_column_stays_within_the_channel_range(self, document: LoadedProject) -> None:
        assert all(VOLUME_OFF <= row.volume <= FULL_VOLUME for row in every_row(document))


class TestTheGrooveReachesTheFile:
    """A tempo the speed column cannot state travels as a table of per-row tick counts and a
    trigger that names it, so the file has to hold the groove the calculator produced and
    re-trigger it wherever the order takes playback.
    """

    @pytest.fixture(name="groove_table")
    def groove_table_fixture(self, groove_document: LoadedProject) -> LoadedTable:
        return groove_document.tables[-1]

    def test_the_groove_takes_the_table_above_the_slices(
        self,
        groove_document: LoadedProject,
        groove_table: LoadedTable,
    ) -> None:
        assert groove_table.id == len(groove_document.instruments)

    def test_the_table_holds_one_entry_per_pattern_row(
        self,
        groove_document: LoadedProject,
        groove_table: LoadedTable,
    ) -> None:
        lengths = {pattern.length for pattern in groove_document.songs[0].patterns}
        assert lengths == {len(groove_table.rows)}

    def test_every_entry_is_a_speed_the_engine_reads(self, groove_table: LoadedTable) -> None:
        assert all(MIN_INITIAL_SPEED <= ticks <= MAX_INITIAL_SPEED for ticks in groove_table.rows)

    def test_the_table_holds_the_groove_the_project_plays(
        self,
        integration_project: Project,
        groove_table: LoadedTable,
    ) -> None:
        project = at_tempo(integration_project, GROOVE_TEMPO)
        groove = calculate_groove(
            RowRate.from_settings(project.settings),
            Meter.from_settings(project.settings, rows=project.song.rows_per_pattern),
            minimum_ticks=MIN_INITIAL_SPEED,
            maximum_ticks=MAX_INITIAL_SPEED,
        )
        assert groove_table.rows == list(groove.ticks)

    def test_the_song_starts_on_the_ticks_its_first_row_lasts(
        self,
        groove_document: LoadedProject,
        groove_table: LoadedTable,
    ) -> None:
        assert groove_document.songs[0].initial_speed == groove_table.rows[0]

    def test_every_pattern_triggers_the_groove_on_its_first_row(
        self,
        groove_document: LoadedProject,
        groove_table: LoadedTable,
    ) -> None:
        trigger = LoadedEffect(
            effect=int(EffectId.SPEED),
            delay=SPEED_EFFECT_DELAY,
            parameter=NO_EFFECT_PARAMETER,
            table_index=groove_table.id,
        )
        triggers = [
            pattern.channels[int(ChannelIndex.DPCM)].rows[0].effects for pattern in groove_document.songs[0].patterns
        ]
        assert triggers == [[trigger]] * len(triggers)

    def test_a_tempo_the_speed_column_states_leaves_every_effect_column_empty(
        self,
        document: LoadedProject,
    ) -> None:
        """The song's own tempo divides into whole ticks, so its document carries the speed
        and nothing beside it.
        """
        assert len(document.tables) == len(document.instruments)
        assert all(row.effects == list(BITPHASE_NO_EFFECTS) for row in every_row(document))


class TestTheInstrumentMacrosArePlayable:
    def test_every_waveform_value_is_one_the_channel_reads(self, document: LoadedProject) -> None:
        values = [
            value for instrument in document.instruments for value in instrument.macro(NesMacroField.PULSE_WIDTH).values
        ]
        assert all(MIN_PULSE_WIDTH <= value <= MAX_PULSE_WIDTH for value in values)

    def test_every_level_is_one_the_channel_reads(self, document: LoadedProject) -> None:
        values = [
            value
            for instrument in document.instruments
            for value in instrument.macro(NesMacroField.VOLUME_OR_RATE).values
        ]
        assert all(MIN_VOLUME_OR_RATE <= value <= MAX_VOLUME_OR_RATE for value in values)

    def test_the_fields_a_reconstruction_leaves_alone_are_left_out(self, document: LoadedProject) -> None:
        """Bitphase reads a field an instrument states no macro for at that field's own default,
        which is the literal volume, the sustained note and the silent sweep a reconstruction asks
        for.
        """
        written = {field for instrument in document.instruments for field in instrument.macros}
        assert written.isdisjoint({"envelope", "soundLength", "sweep", "toneAccumulation"})

    def test_every_macro_circles_from_a_value_it_holds(self, document: LoadedProject) -> None:
        """Playback circles from the loop index once the values run out, so a point past
        them would leave the field nowhere to resume from.
        """
        assert all(
            macro.loop < len(macro.values)
            for instrument in document.instruments
            for macro in instrument.macros.values()
        )

    def test_every_table_loops_on_a_row_it_holds(self, document: LoadedProject) -> None:
        assert all(table.loop < len(table.rows) for table in document.tables)

    def test_every_macro_holds_the_values_a_bitphase_instrument_stores(self, document: LoadedProject) -> None:
        assert all(
            MIN_MACRO_LENGTH <= len(macro.values) <= MAX_MACRO_LENGTH
            for instrument in document.instruments
            for macro in instrument.macros.values()
        )
