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
    MAX_TUNING_PERIOD,
    MIN_TUNING_PERIOD,
    TUNING_TABLE_LENGTH,
    ChipVariant,
)
from sampletones_core.formats.bitphase.specification.instruments import (
    MAX_PULSE_WIDTH,
    MAX_VOLUME_OR_RATE,
    MIN_PULSE_WIDTH,
    MIN_VOLUME_OR_RATE,
    SUSTAINED_SOUND_LENGTH,
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
from tests.suite.bitphase import LoadedNote, LoadedProject, LoadedRow, parse_btp

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
def document(integration_project: Project, document_path: Path) -> LoadedProject:
    write_btp(document_path, project_to_bitphase(integration_project))
    return parse_btp(document_path.read_bytes(), list(CHANNEL_LABELS))


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
        assert any(row.volume_or_rate > 0 for instrument in document.instruments for row in instrument.rows)


class TestTheLoaderReadsWhatWasWritten:
    """Bitphase reconstructs a project field by field, falling back to a default for each
    one it misses, so a field left out of the document reaches playback as that default.
    Reading the file back through the same fallbacks is the contract with the tracker.
    """

    def test_the_song_names_the_chip_it_drives(self, document: LoadedProject) -> None:
        assert document.songs[0].chip_type == CHIP_TYPE_NES

    def test_every_instrument_names_the_chip_whose_rows_it_holds(self, document: LoadedProject) -> None:
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

    def test_each_channel_is_labelled_as_its_position_names_it(self, document: LoadedProject) -> None:
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


class TestTheInstrumentRowsArePlayable:
    def test_every_row_holds_a_waveform_the_channel_reads(self, document: LoadedProject) -> None:
        rows = [row for instrument in document.instruments for row in instrument.rows]
        assert all(MIN_PULSE_WIDTH <= row.pulse_width <= MAX_PULSE_WIDTH for row in rows)

    def test_every_row_holds_a_level_the_channel_reads(self, document: LoadedProject) -> None:
        rows = [row for instrument in document.instruments for row in instrument.rows]
        assert all(MIN_VOLUME_OR_RATE <= row.volume_or_rate <= MAX_VOLUME_OR_RATE for row in rows)

    def test_every_row_reads_its_level_as_a_literal_volume(self, document: LoadedProject) -> None:
        rows = [row for instrument in document.instruments for row in instrument.rows]
        assert all(row.envelope is False for row in rows)

    def test_every_row_holds_the_note_for_as_long_as_the_envelope_runs(self, document: LoadedProject) -> None:
        rows = [row for instrument in document.instruments for row in instrument.rows]
        assert all(row.sound_length == SUSTAINED_SOUND_LENGTH for row in rows)

    def test_every_instrument_loops_on_a_row_it_holds(self, document: LoadedProject) -> None:
        """Playback returns to the loop row once it runs off the end, so a loop point
        past the last row would leave the instrument nowhere to resume from.
        """
        assert all(instrument.loop < len(instrument.rows) for instrument in document.instruments)

    def test_every_table_loops_on_a_row_it_holds(self, document: LoadedProject) -> None:
        assert all(table.loop < len(table.rows) for table in document.tables)

    def test_each_instrument_runs_as_long_as_its_table(self, document: LoadedProject) -> None:
        """The rows and the table advance on their own per-tick counters, so a length
        they share is what keeps the volume envelope aligned with the pitch contour.
        """
        lengths = [
            (len(instrument.rows), len(table.rows)) for instrument, table in zip(document.instruments, document.tables)
        ]
        assert all(rows == table_rows for rows, table_rows in lengths)
