from dataclasses import dataclass
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD, MIN_PITCH, NUM_PERIODS
from sampletones_core.formats.bitphase.btp import project_to_bytes
from sampletones_core.formats.bitphase.builder import project_to_bitphase
from sampletones_core.formats.bitphase.model.pattern import BitphaseRow, EffectCell
from sampletones_core.formats.bitphase.model.project import BitphaseProject
from sampletones_core.formats.bitphase.model.table import BitphaseTable
from sampletones_core.formats.bitphase.notes import pitch_to_note_index
from sampletones_core.formats.bitphase.specification.channels import (
    CHANNEL_LABELS,
    CHANNEL_TO_INDEX,
    ChannelIndex,
)
from sampletones_core.formats.bitphase.specification.effects import (
    MAX_ORNAMENT_POSITION,
    NO_EFFECT_TABLE,
    ORNAMENT_POSITION_DELAY,
    EffectId,
)
from sampletones_core.formats.bitphase.specification.instruments import MAX_TABLE_ID, MIN_TABLE_ID
from sampletones_core.formats.bitphase.specification.patterns import (
    NO_INSTRUMENT_CHANGE,
    NO_TABLE_CHANGE,
    TABLE_COLUMN_OFFSET,
    NoteName,
)
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.sample import Sample
from tests.suite.base import BaseTestSuite
from tests.suite.bitphase import noise_register, note_value, parse_btp, played_notes
from tests.suite.case import BaseRegularTestCase
from tests.suite.transposes import (
    TRANSPOSED_ROWS_PER_PATTERN,
    contour_sample,
    flat_sample,
    note,
    one_channel_project,
    rows_with,
    sounded_pitches,
)

UNIFORM_SETTINGS: Final[ProjectSettings] = ProjectSettings()
UNIFORM_ROW_TICKS: Final[int] = UNIFORM_SETTINGS.speed
GROOVE_SETTINGS: Final[ProjectSettings] = ProjectSettings(tempo=210)
CHANNEL: Final[ChannelName] = ChannelName.PULSE1
FRAMES: Final[int] = 240
LONG_FRAMES: Final[int] = 420
RAISED: Final[int] = 2
LOWERED: Final[int] = -3
NOTE_TRANSPOSE: Final[int] = 5
AFTER_RESET_TRANSPOSE: Final[int] = 1
RAISED_ROW: Final[int] = 3
LOWERED_ROW: Final[int] = 7
RESET_ROW: Final[int] = 10
AFTER_RESET_ROW: Final[int] = 13
LATE_NOTE_ROW: Final[int] = 12
PITCH_OFFSET: Final[int] = 24
FLAT_PITCH: Final[int] = 40
FLAT_FRAMES: Final[int] = 8
SUBMERGED_TRANSPOSE: Final[int] = -20
NOISE_PERIOD: Final[int] = 3
NOISE_TRANSPOSE: Final[int] = -5
LATE_FRAME: Final[int] = 3
SHORT_ORDER: Final[Tuple[Optional[int], ...]] = (0, 1, 2)
LONG_ORDER: Final[Tuple[Optional[int], ...]] = (0, None, None, 1, 2)


def channel_row(
    document: BitphaseProject,
    frame: int,
    row_index: int,
    channel: ChannelName = CHANNEL,
) -> BitphaseRow:
    return document.songs[0].patterns[frame].channels[int(CHANNEL_TO_INDEX[channel])].rows[row_index]


def named_table(document: BitphaseProject, row: BitphaseRow) -> BitphaseTable:
    return next(table for table in document.tables if table.id == row.table - TABLE_COLUMN_OFFSET)


def groove_ticks(document: BitphaseProject) -> Tuple[int, ...]:
    """The ticks each row lasts, read from the table the groove trigger on the DPCM channel names."""
    trigger = document.songs[0].patterns[0].channels[int(ChannelIndex.DPCM)].rows[0].effects[0]
    assert trigger is not None
    return next(table for table in document.tables if table.id == trigger.table_index).rows


def ornament(position: int) -> Tuple[Optional[EffectCell], ...]:
    return (
        EffectCell(
            effect=int(EffectId.ORNAMENT_POSITION),
            delay=ORNAMENT_POSITION_DELAY,
            parameter=position,
            table_index=NO_EFFECT_TABLE,
        ),
    )


@pytest.fixture(name="lead")
def lead_fixture() -> Sample:
    return contour_sample(CHANNEL, FRAMES)


def moved_project(
    voice: Sample,
    *cells: Tuple[int, Row],
    settings: ProjectSettings,
) -> Project:
    return one_channel_project((voice,), CHANNEL, {0: rows_with(*cells)}, [0], settings=settings)


class TestTheCellsATransposeRowWrites:
    """A table cell alone attaches a table while the instrument plays on, so a transpose row names the
    note's table moved by the distance between the note its transpose would write and the note already
    written, and places it at the step the note has reached.
    """

    @pytest.fixture(name="raised")
    def raised_fixture(self, lead: Sample) -> BitphaseProject:
        return project_to_bitphase(
            moved_project(lead, (0, note(lead)), (RAISED_ROW, Row(transpose=RAISED)), settings=UNIFORM_SETTINGS)
        )

    def test_the_row_names_the_notes_table_moved_by_the_transpose(self, raised: BitphaseProject) -> None:
        trigger = named_table(raised, channel_row(raised, 0, 0))
        moved = named_table(raised, channel_row(raised, 0, RAISED_ROW))

        assert moved.rows == tuple(step + RAISED for step in trigger.rows)
        assert moved.loop == trigger.loop

    def test_the_row_leaves_the_note_and_the_instrument_alone(self, raised: BitphaseProject) -> None:
        """A note or an instrument cell restarts the instrument, so the row writes neither."""
        row = channel_row(raised, 0, RAISED_ROW)

        assert (row.note.name, row.instrument) == (int(NoteName.NONE), NO_INSTRUMENT_CHANGE)

    def test_the_row_places_the_table_at_the_step_the_note_reached(self, raised: BitphaseProject) -> None:
        assert channel_row(raised, 0, RAISED_ROW).effects == ornament(RAISED_ROW * UNIFORM_ROW_TICKS)

    def test_the_moved_table_takes_an_id_above_the_slices(self, raised: BitphaseProject) -> None:
        moved = named_table(raised, channel_row(raised, 0, RAISED_ROW))

        assert moved.id == len(raised.instruments) + MIN_TABLE_ID

    def test_a_second_row_moves_the_note_from_where_it_was_written(self, lead: Sample) -> None:
        """Every transpose is measured from the voice's reference, so each row's table is moved from the
        note the note-on wrote, whatever an earlier row moved it to.
        """
        document = project_to_bitphase(
            moved_project(
                lead,
                (0, note(lead)),
                (RAISED_ROW, Row(transpose=RAISED)),
                (LOWERED_ROW, Row(transpose=LOWERED)),
                settings=UNIFORM_SETTINGS,
            )
        )

        trigger = named_table(document, channel_row(document, 0, 0))
        moved = named_table(document, channel_row(document, 0, LOWERED_ROW))

        assert moved.rows == tuple(step + LOWERED for step in trigger.rows)
        assert channel_row(document, 0, LOWERED_ROW).effects == ornament(LOWERED_ROW * UNIFORM_ROW_TICKS)

    def test_the_shift_counts_from_the_transpose_the_note_started_at(self, lead: Sample) -> None:
        document = project_to_bitphase(
            moved_project(
                lead,
                (0, note(lead, NOTE_TRANSPOSE)),
                (RAISED_ROW, Row(transpose=RAISED)),
                settings=UNIFORM_SETTINGS,
            )
        )

        trigger = named_table(document, channel_row(document, 0, 0))
        moved = named_table(document, channel_row(document, 0, RAISED_ROW))

        assert moved.rows == tuple(step + RAISED - NOTE_TRANSPOSE for step in trigger.rows)

    def test_a_note_on_starts_from_its_own_table_again(self, lead: Sample) -> None:
        document = project_to_bitphase(
            moved_project(
                lead,
                (0, note(lead)),
                (RAISED_ROW, Row(transpose=RAISED)),
                (RESET_ROW, note(lead)),
                (AFTER_RESET_ROW, Row(transpose=LOWERED)),
                settings=UNIFORM_SETTINGS,
            )
        )

        trigger = channel_row(document, 0, 0)
        after = channel_row(document, 0, AFTER_RESET_ROW)

        assert channel_row(document, 0, RESET_ROW).table == trigger.table
        assert named_table(document, after).rows == tuple(
            step + LOWERED for step in named_table(document, trigger).rows
        )
        assert after.effects == ornament((AFTER_RESET_ROW - RESET_ROW) * UNIFORM_ROW_TICKS)

    def test_a_row_returning_to_the_notes_transpose_names_the_notes_own_table(self, lead: Sample) -> None:
        document = project_to_bitphase(
            moved_project(
                lead,
                (0, note(lead)),
                (RAISED_ROW, Row(transpose=RAISED)),
                (LOWERED_ROW, Row(transpose=0)),
                settings=UNIFORM_SETTINGS,
            )
        )

        assert channel_row(document, 0, LOWERED_ROW).table == channel_row(document, 0, 0).table

    def test_a_row_restating_the_transpose_in_force_writes_no_table(self, lead: Sample) -> None:
        document = project_to_bitphase(
            moved_project(
                lead,
                (0, note(lead)),
                (RAISED_ROW, Row(transpose=RAISED)),
                (LOWERED_ROW, Row(transpose=RAISED)),
                settings=UNIFORM_SETTINGS,
            )
        )

        assert channel_row(document, 0, LOWERED_ROW).table == NO_TABLE_CHANGE

    def test_rows_moving_a_slice_alike_share_one_table(self, lead: Sample) -> None:
        document = project_to_bitphase(
            moved_project(
                lead,
                (0, note(lead)),
                (RAISED_ROW, Row(transpose=RAISED)),
                (RESET_ROW, note(lead)),
                (AFTER_RESET_ROW, Row(transpose=RAISED)),
                settings=UNIFORM_SETTINGS,
            )
        )

        assert channel_row(document, 0, AFTER_RESET_ROW).table == channel_row(document, 0, RAISED_ROW).table

    def test_a_transpose_below_the_range_moves_the_note_where_a_note_on_would_write_it(self) -> None:
        """A note-on at the new transpose writes its note by the low-pitch rule, so the moved table
        reaches the note that rule writes, and a flat slice sounds the lowest pitch the song plays.
        """
        flat = flat_sample(CHANNEL, FLAT_PITCH, FLAT_FRAMES)
        document = project_to_bitphase(
            moved_project(
                flat,
                (0, note(flat)),
                (RAISED_ROW, Row(transpose=SUBMERGED_TRANSPOSE)),
                settings=UNIFORM_SETTINGS,
            )
        )

        moved = named_table(document, channel_row(document, 0, RAISED_ROW))

        assert moved.rows == (pitch_to_note_index(MIN_PITCH) - pitch_to_note_index(FLAT_PITCH),)


class TestTheStepANoteHasReached:
    """A note's table advances a step every tick from the note on, so the step a transpose row places
    its table at counts the ticks every row since the note lasts, across the frames between them.
    """

    def test_a_groove_counts_each_row_at_its_own_length(self, lead: Sample) -> None:
        document = project_to_bitphase(
            moved_project(lead, (0, note(lead)), (RAISED_ROW, Row(transpose=RAISED)), settings=GROOVE_SETTINGS)
        )

        assert channel_row(document, 0, RAISED_ROW).effects == ornament(sum(groove_ticks(document)[:RAISED_ROW]))

    def test_the_rows_of_every_frame_between_are_counted(self, lead: Sample) -> None:
        """A frame leaving the channel empty plays on with the note it carries."""
        project = one_channel_project(
            (lead,),
            CHANNEL,
            {0: rows_with((LATE_NOTE_ROW, note(lead))), 1: rows_with((RAISED_ROW, Row(transpose=RAISED)))},
            [0, None, 1],
            settings=GROOVE_SETTINGS,
        )
        document = project_to_bitphase(project)
        ticks = groove_ticks(document)

        elapsed = sum(ticks[LATE_NOTE_ROW:]) + sum(ticks) + sum(ticks[:RAISED_ROW])

        assert channel_row(document, 2, RAISED_ROW).effects == ornament(elapsed)

    def test_a_step_past_the_ornament_position_names_a_table_opening_on_it(self) -> None:
        long = contour_sample(CHANNEL, LONG_FRAMES)
        project = one_channel_project(
            (long,),
            CHANNEL,
            {0: rows_with((0, note(long))), 1: rows_with((0, Row(transpose=RAISED)))},
            [0, None, None, 1],
            settings=UNIFORM_SETTINGS,
        )
        document = project_to_bitphase(project)
        reached = LATE_FRAME * TRANSPOSED_ROWS_PER_PATTERN * UNIFORM_ROW_TICKS

        trigger = named_table(document, channel_row(document, 0, 0))
        row = channel_row(document, LATE_FRAME, 0)
        opening = named_table(document, row)

        assert reached > MAX_ORNAMENT_POSITION
        assert row.effects == (None,)
        assert [opening.rows[opening.position_at(tick)] for tick in range(LONG_FRAMES)] == [
            trigger.rows[trigger.position_at(reached + tick)] + RAISED for tick in range(LONG_FRAMES)
        ]


class TestTheTablesADocumentHolds:
    """The table column names one base-36 digit, so a document whose transpose rows move its notes to
    more tables than it can name is refused.
    """

    @staticmethod
    def _spread(transposes: int) -> Project:
        """A flat slice moved by ``transposes`` distinct transposes, one per row after its note."""
        flat = flat_sample(CHANNEL, FLAT_PITCH, FLAT_FRAMES)
        rows_per_frame = TRANSPOSED_ROWS_PER_PATTERN - 1
        patterns = {
            frame: rows_with(
                (0, note(flat)),
                *(
                    (row_index, Row(transpose=frame * rows_per_frame + row_index))
                    for row_index in range(1, TRANSPOSED_ROWS_PER_PATTERN)
                    if frame * rows_per_frame + row_index <= transposes
                ),
            )
            for frame in range((transposes + rows_per_frame - 1) // rows_per_frame)
        }
        return one_channel_project((flat,), CHANNEL, patterns, list(patterns), settings=UNIFORM_SETTINGS)

    def test_a_document_filling_the_table_column_is_written(self) -> None:
        room = MAX_TABLE_ID - MIN_TABLE_ID
        document = project_to_bitphase(self._spread(room))

        assert max(table.id for table in document.tables) == MAX_TABLE_ID

    def test_a_document_needing_more_tables_is_refused(self) -> None:
        room = MAX_TABLE_ID - MIN_TABLE_ID
        with pytest.raises(ValueError, match="tables"):
            project_to_bitphase(self._spread(room + 1))


class TestANoiseTransposeWalksThePeriods:
    """A noise transpose walks the period around the sixteen the channel has, and the moved table takes
    whatever note the noise mapping writes for the new period, so it follows that mapping wherever the
    note index sits.
    """

    def test_the_moved_table_sounds_the_walked_period(self) -> None:
        drum = flat_sample(ChannelName.NOISE, NOISE_PERIOD, FLAT_FRAMES)
        project = one_channel_project(
            (drum,),
            ChannelName.NOISE,
            {0: rows_with((0, note(drum)), (RAISED_ROW, Row(transpose=NOISE_TRANSPOSE)))},
            [0],
            settings=UNIFORM_SETTINGS,
        )
        document = project_to_bitphase(project)

        trigger = channel_row(document, 0, 0, ChannelName.NOISE)
        moved = named_table(document, channel_row(document, 0, RAISED_ROW, ChannelName.NOISE))
        index = note_value(trigger.note) + moved.rows[0]  # type: ignore[arg-type]

        assert noise_register(index) == MAX_PERIOD - (NOISE_PERIOD + NOISE_TRANSPOSE) % NUM_PERIODS


def replayed(document: BitphaseProject, channel_name: ChannelName) -> List[Optional[int]]:
    """What Bitphase sounds on one channel each tick: the pitch, or on noise the period register."""
    loaded = parse_btp(project_to_bytes(document), list(CHANNEL_LABELS))
    notes = played_notes(loaded, int(CHANNEL_TO_INDEX[channel_name]))
    if channel_name == ChannelName.NOISE:
        return [None if index is None else noise_register(index) for index in notes]

    return [None if index is None else index + PITCH_OFFSET for index in notes]


class TestATransposedSongSoundsTheSongsPitch(BaseTestSuite):
    """Played the way Bitphase reads its rows, a song whose transpose rows move a sounding note, cross
    frames under a groove, and meet a note-on starting over sounds the pitch the song's walk sounds on
    every tick the song sounds.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel: ChannelName
        frames: int
        order: Tuple[Optional[int], ...]

    test_cases: Tuple["TestATransposedSongSoundsTheSongsPitch.TestCase", ...] = (
        TestCase(label="pulse", channel=ChannelName.PULSE1, frames=FRAMES, order=SHORT_ORDER),
        TestCase(label="triangle", channel=ChannelName.TRIANGLE, frames=FRAMES, order=SHORT_ORDER),
        TestCase(label="noise", channel=ChannelName.NOISE, frames=FRAMES, order=SHORT_ORDER),
        TestCase(label="pulse_past_the_ornament", channel=ChannelName.PULSE1, frames=LONG_FRAMES, order=LONG_ORDER),
        TestCase(
            label="triangle_past_the_ornament", channel=ChannelName.TRIANGLE, frames=LONG_FRAMES, order=LONG_ORDER
        ),
        TestCase(label="noise_past_the_ornament", channel=ChannelName.NOISE, frames=LONG_FRAMES, order=LONG_ORDER),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_sounding_tick_plays_the_songs_pitch(
        self,
        test_case: "TestATransposedSongSoundsTheSongsPitch.TestCase",
    ) -> None:
        voice = contour_sample(test_case.channel, test_case.frames)
        patterns = {
            0: rows_with((0, note(voice)), (RAISED_ROW, Row(transpose=RAISED))),
            1: rows_with(
                (2, Row(transpose=LOWERED)),
                (RESET_ROW, note(voice)),
                (AFTER_RESET_ROW, Row(transpose=AFTER_RESET_TRANSPOSE)),
            ),
            2: rows_with((RAISED_ROW, Row(transpose=LOWERED)), (LOWERED_ROW, Row(transpose=0))),
        }
        project = one_channel_project(
            (voice,),
            test_case.channel,
            patterns,
            list(test_case.order),
            settings=GROOVE_SETTINGS,
        )

        sounded = sounded_pitches(project, test_case.channel)
        played = replayed(project_to_bitphase(project), test_case.channel)

        assert len(played) == len(sounded)
        assert [tick for tick, pitch in enumerate(sounded) if pitch is not None and played[tick] != pitch] == []
