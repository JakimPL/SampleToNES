import math
from typing import Final, List

import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.formats.bitphase.builder import (
    PREVIEW_REST_PATTERN_ID,
    PREVIEW_SPEED,
    PREVIEW_TRIGGER_ROW,
    instrument_to_bitphase,
    sample_to_bitphase,
)
from sampletones_core.formats.bitphase.identifiers import format_instrument_id
from sampletones_core.formats.bitphase.model.project import BitphaseProject
from sampletones_core.formats.bitphase.notes import (
    noise_period_to_note_index,
    note_index_to_note_cell,
    pitch_to_note_index,
)
from sampletones_core.formats.bitphase.specification.channels import CHANNEL_COUNT, ChannelIndex
from sampletones_core.formats.bitphase.specification.chip import CHIP_TYPE_NES
from sampletones_core.formats.bitphase.specification.instruments import MAX_TABLE_ID, MIN_INSTRUMENT_ID, MIN_TABLE_ID
from sampletones_core.formats.bitphase.specification.patterns import (
    FIRST_PATTERN_ID,
    FULL_VOLUME,
    MAX_PATTERN_LENGTH,
    MIN_PATTERN_LENGTH,
    NO_INSTRUMENT_CHANGE,
    NO_TABLE_CHANGE,
    TABLE_COLUMN_OFFSET,
    NoteName,
)

from .conftest import NES_FREQUENCY, REFERENCE_PITCH, build_features, build_instrument, build_sample

VOLUME_ENVELOPE: Final[List[int]] = [15, 10, 5, 0]
NOISE_PERIOD: Final[int] = 4
LONG_ENVELOPE_FRAMES: Final[int] = 4000


@pytest.fixture(name="project")
def project_fixture() -> BitphaseProject:
    return sample_to_bitphase(
        build_sample(
            "Kick",
            build_instrument("Kick (pulse1)", build_features(VOLUME_ENVELOPE)),
            build_instrument(
                "Kick (noise)",
                build_features(VOLUME_ENVELOPE, initial_pitch=NOISE_PERIOD),
                generator=GeneratorName.NOISE,
            ),
        )
    )


class TestEverySliceBecomesAVoice:
    def test_each_slice_yields_one_instrument(self, project: BitphaseProject) -> None:
        assert [instrument.name for instrument in project.instruments] == ["Kick (pulse1)", "Kick (noise)"]

    def test_each_slice_yields_the_table_that_carries_its_contour(self, project: BitphaseProject) -> None:
        assert [table.name for table in project.tables] == ["Kick (pulse1)", "Kick (noise)"]

    def test_instruments_are_numbered_from_the_first_the_column_names(self, project: BitphaseProject) -> None:
        assert [instrument.id for instrument in project.instruments] == [
            format_instrument_id(MIN_INSTRUMENT_ID),
            format_instrument_id(MIN_INSTRUMENT_ID + 1),
        ]

    def test_tables_are_numbered_alongside_the_instruments(self, project: BitphaseProject) -> None:
        assert [table.id for table in project.tables] == [MIN_TABLE_ID, MIN_TABLE_ID + 1]

    def test_every_instrument_declares_the_chip_whose_rows_it_holds(self, project: BitphaseProject) -> None:
        """A document that leaves the chip unnamed loads as an AY instrument, so the
        instrument rows would be read under the wrong layout.
        """
        assert {instrument.chip_type for instrument in project.instruments} == {CHIP_TYPE_NES}

    def test_the_song_declares_the_chip_it_drives(self, project: BitphaseProject) -> None:
        assert project.songs[0].chip_type == CHIP_TYPE_NES


class TestThePreviewPattern:
    def test_the_pattern_spans_every_channel(self, project: BitphaseProject) -> None:
        assert len(project.songs[0].patterns[0].channels) == CHANNEL_COUNT

    def test_each_voice_is_triggered_on_the_channel_it_was_reconstructed_for(
        self,
        project: BitphaseProject,
    ) -> None:
        channels = project.songs[0].patterns[0].channels
        triggered = {
            index: channel.rows[PREVIEW_TRIGGER_ROW].instrument
            for index, channel in enumerate(channels)
            if channel.rows[PREVIEW_TRIGGER_ROW].instrument != NO_INSTRUMENT_CHANGE
        }
        assert triggered == {
            int(ChannelIndex.SQUARE1): MIN_INSTRUMENT_ID,
            int(ChannelIndex.NOISE): MIN_INSTRUMENT_ID + 1,
        }

    def test_a_trigger_attaches_the_voice_table(self, project: BitphaseProject) -> None:
        row = project.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[PREVIEW_TRIGGER_ROW]
        assert row.table == MIN_TABLE_ID + TABLE_COLUMN_OFFSET

    def test_a_trigger_passes_the_instrument_volume_through(self, project: BitphaseProject) -> None:
        """Row 15 of the volume table is the identity, so the instrument's own envelope
        reaches the channel unscaled.
        """
        row = project.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[PREVIEW_TRIGGER_ROW]
        assert row.volume == FULL_VOLUME

    def test_a_pitched_trigger_names_the_reconstructed_note(self, project: BitphaseProject) -> None:
        row = project.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[PREVIEW_TRIGGER_ROW]
        assert row.note == note_index_to_note_cell(pitch_to_note_index(REFERENCE_PITCH))

    def test_a_noise_trigger_names_the_note_that_selects_its_period(self, project: BitphaseProject) -> None:
        row = project.songs[0].patterns[0].channels[int(ChannelIndex.NOISE)].rows[PREVIEW_TRIGGER_ROW]
        assert row.note == note_index_to_note_cell(noise_period_to_note_index(NOISE_PERIOD))

    def test_the_lines_after_the_trigger_leave_the_channel_alone(self, project: BitphaseProject) -> None:
        rows = project.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows
        assert all(row.instrument == NO_INSTRUMENT_CHANGE for row in rows[1:])
        assert all(row.table == NO_TABLE_CHANGE for row in rows[1:])

    def test_the_pattern_length_stays_within_what_bitphase_holds(self, project: BitphaseProject) -> None:
        length = project.songs[0].patterns[0].length
        assert MIN_PATTERN_LENGTH <= length <= MAX_PATTERN_LENGTH

    def test_every_channel_of_the_pattern_is_as_long_as_the_pattern(self, project: BitphaseProject) -> None:
        pattern = project.songs[0].patterns[0]
        assert all(len(channel.rows) == pattern.length for channel in pattern.channels)


class TestTheOrderCoversTheLongestInstrument:
    """Playback returns to the start of the order, so a document whose order runs out
    before its longest instrument does would retrigger the slice mid-note.
    """

    @pytest.fixture(name="long_project")
    def long_project_fixture(self) -> BitphaseProject:
        return sample_to_bitphase(
            build_sample(
                "Pad",
                build_instrument("Pad (pulse1)", build_features([15] * LONG_ENVELOPE_FRAMES)),
            )
        )

    def test_a_short_slice_plays_from_one_position(self, project: BitphaseProject) -> None:
        assert project.pattern_order == (FIRST_PATTERN_ID,)

    def test_a_long_slice_rests_for_as_many_positions_as_it_needs(self, long_project: BitphaseProject) -> None:
        pattern_length = long_project.songs[0].patterns[0].length
        positions = math.ceil(LONG_ENVELOPE_FRAMES / (pattern_length * PREVIEW_SPEED))
        assert long_project.pattern_order == (FIRST_PATTERN_ID,) + (PREVIEW_REST_PATTERN_ID,) * (positions - 1)

    def test_the_resting_positions_name_a_pattern_the_song_holds(self, long_project: BitphaseProject) -> None:
        held = {pattern.id for pattern in long_project.songs[0].patterns}
        assert set(long_project.pattern_order) <= held

    def test_a_resting_position_leaves_every_channel_silent(self, long_project: BitphaseProject) -> None:
        rest = long_project.songs[0].patterns[PREVIEW_REST_PATTERN_ID]
        assert all(row.instrument == NO_INSTRUMENT_CHANGE for channel in rest.channels for row in channel.rows)


class TestOneSliceOnItsOwn:
    def test_a_single_slice_becomes_a_playable_document(self) -> None:
        project = instrument_to_bitphase(
            build_instrument("Lead", build_features(VOLUME_ENVELOPE, arpeggio=[0, 3, 5, 7]))
        )
        assert len(project.instruments) == 1
        assert len(project.tables) == 1

    def test_the_document_is_named_after_the_slice(self) -> None:
        project = instrument_to_bitphase(build_instrument("Lead", build_features(VOLUME_ENVELOPE)))
        assert project.name == "Lead"

    def test_the_engine_tick_rate_carries_the_reconstruction_rate(self) -> None:
        project = instrument_to_bitphase(build_instrument("Lead", build_features(VOLUME_ENVELOPE)))
        assert project.songs[0].interrupt_frequency == NES_FREQUENCY

    def test_a_noise_slice_reaches_the_noise_channel(self) -> None:
        project = instrument_to_bitphase(
            build_instrument(
                "Hat",
                build_features(VOLUME_ENVELOPE, arpeggio=[0, 1, 2, 3], initial_pitch=NOISE_PERIOD),
                generator=GeneratorName.NOISE,
            )
        )
        row = project.songs[0].patterns[0].channels[int(ChannelIndex.NOISE)].rows[PREVIEW_TRIGGER_ROW]
        assert row.note.name != int(NoteName.NONE)

    def test_a_noise_table_holds_offsets_within_one_period_cycle(self) -> None:
        project = instrument_to_bitphase(
            build_instrument(
                "Hat",
                build_features(VOLUME_ENVELOPE, arpeggio=[0, -1, -2, -3], initial_pitch=NOISE_PERIOD),
                generator=GeneratorName.NOISE,
            )
        )
        assert all(0 <= offset < NUM_PERIODS for offset in project.tables[0].rows)


class TestCapacityLimits:
    """A pattern's table column names one base-36 digit, so a document reaching past
    what the column can name is refused rather than written unplayable.
    """

    def test_a_document_filling_the_table_column_is_written(self) -> None:
        voices = MAX_TABLE_ID + 1
        request = build_sample(
            "Wide",
            *(build_instrument(f"Slice {index}", build_features(VOLUME_ENVELOPE)) for index in range(voices)),
        )
        assert len(sample_to_bitphase(request).tables) == voices

    def test_a_document_past_the_table_column_is_refused(self) -> None:
        voices = MAX_TABLE_ID + 2
        request = build_sample(
            "Wider",
            *(build_instrument(f"Slice {index}", build_features(VOLUME_ENVELOPE)) for index in range(voices)),
        )
        with pytest.raises(ValueError, match="tables"):
            sample_to_bitphase(request)
