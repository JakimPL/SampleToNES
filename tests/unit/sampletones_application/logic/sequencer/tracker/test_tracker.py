from dataclasses import dataclass
from typing import Final, List, Tuple

import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import SequencerTrackerViewModel
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_TRANSPOSE, MAX_VOLUME
from sampletones_core.project.patterns.pitch import Note, Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.utils.display import NOTE_OFF, display_id, display_volume
from sampletones_shared.constants.symbols import MIXED
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.sequencer import (
    UNKNOWN_SAMPLE,
    UNKNOWN_SAMPLE_ID,
    fill_frame,
    render_frame,
    render_slots,
    sample_reconstruction,
)

FRAME_ROWS: Final[int] = 4
EMPTY: Final[str] = ".. ... . | .. ... . | .. ... . | .. ... ."
LEAD: Final[str] = "00"
BASS: Final[str] = "01"
PAD: Final[str] = "02"
CONTEXT_REACH: Final[int] = 2
VOLUME_BEFORE: Final[int] = 5
VOLUME_AFTER: Final[int] = 9


def _controller() -> ProjectController:
    return ProjectController(ProjectManager())


def _row(
    controller: ProjectController,
    channel: ChannelName,
    row_index: int = 0,
) -> Row:
    song = controller.project.song
    pattern_index = song.order[0][channel]
    return song[channel].get_row(pattern_index, row_index)


def _place_voice(
    controller: ProjectController,
    channel: ChannelName,
    voice_id: str,
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(
        channel,
        pattern_index,
        0,
        command=NoteOn(voice_id=voice_id),
    )


@dataclass(frozen=True, kw_only=True)
class Grid:
    """A four-row frame with two samples and an instrument, the state a sample-column case starts from."""

    controller: ProjectController
    logic: SequencerTrackerLogic
    voice_ids: Tuple[str, ...]


@pytest.fixture
def grid() -> Grid:
    """A frame short enough for a case to state whole, beside a sample over the first pulse and the
    triangle, one over the second pulse, and an instrument.

    Which channels a sample plays on is what the sample column's pitch and volume follow, and the
    instrument is what takes a channel away from a sample playing above it.
    """
    controller = _controller()
    logic = SequencerTrackerLogic(controller)
    logic.set_rows_per_pattern(FRAME_ROWS)
    lead = controller.add_sample(
        sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
        name="lead",
    )
    bass = controller.add_sample(
        sample_reconstruction([ChannelName.PULSE2]),
        name="bass",
    )
    pad = controller.add_instrument(new_instrument("pad"))
    return Grid(
        controller=controller,
        logic=logic,
        voice_ids=(lead.id, bass.id, pad.id),
    )


class TestClearCell:
    def test_a_channel_cell_clears_only_that_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, pitch=Step(value=5))
        logic.set_row(ChannelName.PULSE2, 0, pitch=Step(value=7))

        logic.clear_cell(0, ChannelName.PULSE1)

        assert _row(controller, ChannelName.PULSE1).pitch is None
        assert _row(controller, ChannelName.PULSE2).pitch == Step(value=7)

    def test_the_sample_column_clears_every_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        for channel in ChannelName.items():
            logic.set_row(channel, 0, pitch=Step(value=5))

        logic.clear_cell(0, None)

        for channel in ChannelName.items():
            assert _row(controller, channel).pitch is None


class TestClearCellSubcolumn:
    def test_a_channel_cell_clears_one_subcolumn_of_its_own(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, pitch=Step(value=5), volume=10)

        logic.clear_cell_subcolumn(0, ChannelName.PULSE1, SubColumn.TRANSPOSE)

        row = _row(controller, ChannelName.PULSE1)
        assert row.pitch is None
        assert row.volume == 10

    def test_the_sample_column_clears_the_voice_from_every_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_row_sample(0, sample.id)
        logic.set_note_off(ChannelName.NOISE, 0)

        logic.clear_cell_subcolumn(0, None, SubColumn.VOICE)

        for channel in ChannelName.items():
            assert _row(controller, channel).command is None

    def test_the_sample_column_clears_transpose_from_the_sample_channels(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_row_sample(0, sample.id)
        for channel in ChannelName.items():
            logic.set_row(channel, 0, pitch=Step(value=5))

        logic.clear_cell_subcolumn(0, None, SubColumn.TRANSPOSE)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            assert _row(controller, channel).pitch is None

        for channel in (ChannelName.PULSE2, ChannelName.NOISE):
            assert _row(controller, channel).pitch == Step(value=5)


class TestWriteCell:
    def test_a_sample_in_the_sample_column_spreads_over_its_channels(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )

        logic.write_cell(0, None, sample.id, None, None)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            assert isinstance(_row(controller, channel).command, NoteOn)

        for channel in (ChannelName.PULSE2, ChannelName.NOISE):
            assert _row(controller, channel).command is None

    def test_a_sample_in_a_channel_cell_lands_on_that_channel(self) -> None:
        """A cell writes the voice into its own channel's pattern, whichever channels the sample covers."""
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1]),
            name="lead",
        )

        logic.write_cell(0, ChannelName.NOISE, sample.id, None, None)

        command = _row(controller, ChannelName.NOISE).command
        assert isinstance(command, NoteOn)
        assert command.voice_id == sample.id
        assert _row(controller, ChannelName.PULSE1).command is None

    def test_a_voice_and_a_pitch_land_together_in_a_channel_cell(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="lead")

        logic.write_cell(0, ChannelName.PULSE1, sample.id, Note(value=60), None)

        row = _row(controller, ChannelName.PULSE1)
        assert row.command == NoteOn(voice_id=sample.id)
        assert row.pitch == Note(value=60)

    def test_a_sample_and_a_pitch_in_the_sample_column_reach_the_channels_the_sample_spreads_over(self) -> None:
        """The sample is placed first, so the pitch finds the channels it has just covered."""
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )

        logic.write_cell(0, None, sample.id, Note(value=60), None)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            assert _row(controller, channel).command == NoteOn(voice_id=sample.id)
            assert _row(controller, channel).pitch == Note(value=60)

        for channel in (ChannelName.PULSE2, ChannelName.NOISE):
            assert _row(controller, channel).pitch is None

    def test_a_volume_in_a_channel_cell_leaves_the_rest_of_the_cell_standing(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, pitch=Step(value=5))

        logic.write_cell(0, ChannelName.PULSE1, None, None, 10)

        row = _row(controller, ChannelName.PULSE1)
        assert row.pitch == Step(value=5)
        assert row.volume == 10

    def test_an_edit_carrying_no_value_leaves_the_frame_alone(self) -> None:
        """Typing a sample index the project has no sample for creates no pattern."""
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        controller.append_frame()
        logic.select_frame(1)

        logic.write_cell(0, ChannelName.PULSE1, None, None, None)

        assert controller.project.song.order[1][ChannelName.PULSE1] is None


class TestCutNote:
    def test_a_channel_cell_cuts_that_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.cut_note(0, ChannelName.PULSE1)

        assert isinstance(_row(controller, ChannelName.PULSE1).command, NoteOff)
        assert _row(controller, ChannelName.PULSE2).command is None

    def test_the_sample_column_cuts_every_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.cut_note(0, None)

        for channel in ChannelName.items():
            assert isinstance(_row(controller, channel).command, NoteOff)


class TestFrameRowCount:
    def test_counts_the_rows_the_grid_builds(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        assert logic.frame_row_count() == len(logic.build_grid().rows)

    def test_an_empty_frame_counts_editable_rows(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        controller.append_frame()
        logic.select_frame(1)

        assert logic.frame_row_count() == controller.project.song.rows_per_pattern

    def test_an_order_without_frames_counts_nothing(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        controller.remove_frame(0)

        assert logic.frame_row_count() == 0


@dataclass(frozen=True, kw_only=True)
class ThreeFrames:
    """A song of three short frames with the middle one shown."""

    controller: ProjectController
    logic: SequencerTrackerLogic


@pytest.fixture
def three_frames() -> ThreeFrames:
    """Three frames of :data:`FRAME_ROWS` rows, a volume on the first frame's last row and on the last
    frame's first row, so the rows standing either side of the middle frame tell themselves apart.
    """
    controller = _controller()
    controller.set_rows_per_pattern(FRAME_ROWS)
    controller.append_frame()
    controller.append_frame()
    logic = SequencerTrackerLogic(controller)
    logic.set_cell_subcolumn(FRAME_ROWS - 1, ChannelName.PULSE1, volume=VOLUME_BEFORE)
    logic.select_frame(2)
    logic.set_cell_subcolumn(0, ChannelName.PULSE1, volume=VOLUME_AFTER)
    logic.select_frame(1)
    return ThreeFrames(controller=controller, logic=logic)


class TestTheSongAroundTheFrame:
    """The grid carries the rows the song plays either side of the shown frame, as far as it reaches."""

    def test_the_grid_carries_the_rows_either_side(self, three_frames: ThreeFrames) -> None:
        three_frames.logic.set_reach(CONTEXT_REACH)

        grid = three_frames.logic.build_grid()

        assert [(row.frame_index, row.row.index) for row in grid.lead] == [(0, 2), (0, 3)]
        assert [(row.frame_index, row.row.index) for row in grid.trail] == [(2, 0), (2, 1)]

    def test_a_neighboring_row_reads_as_it_does_in_its_own_frame(self, three_frames: ThreeFrames) -> None:
        three_frames.logic.set_reach(CONTEXT_REACH)

        grid = three_frames.logic.build_grid()

        assert grid.lead[-1].row == three_frames.logic.frame_rows(0)[FRAME_ROWS - 1]
        assert grid.trail[0].row == three_frames.logic.frame_rows(2)[0]
        assert grid.lead[-1].row.cells[ChannelName.PULSE1].volume == display_volume(VOLUME_BEFORE)
        assert grid.trail[0].row.cells[ChannelName.PULSE1].volume == display_volume(VOLUME_AFTER)

    def test_without_a_reach_the_grid_holds_the_frame_alone(self, three_frames: ThreeFrames) -> None:
        grid = three_frames.logic.build_grid()

        assert grid.lead == ()
        assert grid.trail == ()
        assert len(grid.rows) == FRAME_ROWS

    def test_a_new_reach_builds_the_grid_and_the_same_one_builds_nothing(self, three_frames: ThreeFrames) -> None:
        pushed: List[SequencerTrackerViewModel] = []
        three_frames.logic.on_tracker_changed = pushed.append

        three_frames.logic.set_reach(CONTEXT_REACH)
        three_frames.logic.set_reach(CONTEXT_REACH)

        assert len(pushed) == 1
        assert len(pushed[0].lead) == CONTEXT_REACH


class TestSelectingAFrame:
    """A frame is built when it is shown, and the frame already shown is only reported again."""

    def test_the_shown_frame_is_reported_and_builds_nothing(self, three_frames: ThreeFrames) -> None:
        pushed: List[SequencerTrackerViewModel] = []
        reported: List[int] = []
        three_frames.logic.on_tracker_changed = pushed.append
        three_frames.logic.on_frame_changed = reported.append

        three_frames.logic.select_frame(1)

        assert pushed == []
        assert reported == [1]

    def test_another_frame_is_built_and_reported(self, three_frames: ThreeFrames) -> None:
        pushed: List[SequencerTrackerViewModel] = []
        reported: List[int] = []
        three_frames.logic.on_tracker_changed = pushed.append
        three_frames.logic.on_frame_changed = reported.append

        three_frames.logic.select_frame(2)

        assert [grid.frame_index for grid in pushed] == [2]
        assert reported == [2]


class TestRowAccess:
    def test_reads_the_stored_row(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, pitch=Step(value=5))

        row = logic.row(ChannelName.PULSE1, 0)

        assert row is not None
        assert row.pitch == Step(value=5)

    def test_a_channel_without_a_pattern_has_no_row(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        controller.append_frame()
        logic.select_frame(1)

        assert logic.row(ChannelName.PULSE1, 0) is None


class TestReferencedChannels:
    def test_one_placement_reports_the_samples_whole_span(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        _place_voice(controller, ChannelName.PULSE1, sample.id)

        assert logic.referenced_channels(0) == frozenset(
            {
                ChannelName.PULSE1,
                ChannelName.TRIANGLE,
            }
        )

    def test_a_row_naming_no_sample_references_no_channel(self) -> None:
        """Nothing plays there either, so a pitch or a volume reaches no channel while the voice
        slot still reads every one of them."""
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_note_off(ChannelName.PULSE1, 0)

        assert logic.referenced_channels(0) == frozenset()
        assert logic.relevant_channels(0) == []
        assert logic.note_channels(0) == ChannelName.items()


class TestSetNoteOff:
    def test_set_note_off_writes_note_off_command(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.set_note_off(ChannelName.PULSE1, 0)

        assert isinstance(
            _row(controller, ChannelName.PULSE1).command,
            NoteOff,
        )

    def test_set_note_off_all_generators_cuts_every_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.set_note_off_all_generators(0)

        for channel in ChannelName.items():
            assert isinstance(_row(controller, channel).command, NoteOff)


class TestSetSampleInstrument:
    def test_fills_only_used_generators(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )

        logic.set_row_sample(0, sample.id)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            command = _row(controller, channel).command
            assert isinstance(command, NoteOn)
            assert command.voice_id == sample.id

        for channel in (ChannelName.PULSE2, ChannelName.NOISE):
            assert _row(controller, channel).command is None

    def test_clears_channels_the_new_sample_does_not_use(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        stale = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE2]),
            name="bass",
        )
        pattern_index = controller.project.song.order[0][ChannelName.PULSE2]
        controller.set_row(
            ChannelName.PULSE2,
            pattern_index,
            0,
            command=NoteOn(voice_id=stale.id),
            volume=15,
        )

        lead = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1]),
            name="lead",
        )
        logic.set_row_sample(0, lead.id)

        assert _row(controller, ChannelName.PULSE1).command is not None
        cleared = _row(controller, ChannelName.PULSE2)
        assert cleared.command is None
        assert cleared.volume is None

    def test_none_sample_clears_the_whole_row(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1]),
            name="lead",
        )
        logic.set_row_sample(0, sample.id)

        logic.set_row_sample(0, None)

        for channel in ChannelName.items():
            assert _row(controller, channel).command is None


class TestSampleSubcolumn:
    def test_synchronizes_across_relevant_channels_even_without_instrument(
        self,
    ) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        _place_voice(controller, ChannelName.PULSE1, sample.id)

        logic.set_sample_subcolumn(0, pitch=Step(value=5))
        logic.set_sample_subcolumn(0, volume=10)

        carrier = _row(controller, ChannelName.PULSE1)
        assert carrier.command is not None
        assert carrier.pitch == Step(value=5)
        assert carrier.volume == 10

        synced = _row(controller, ChannelName.TRIANGLE)
        assert synced.command is None
        assert synced.pitch == Step(value=5)
        assert synced.volume == 10

        for channel in (ChannelName.PULSE2, ChannelName.NOISE):
            row = _row(controller, channel)
            assert row.pitch is None
            assert row.volume is None

    def test_clear_removes_one_subcolumn_across_relevant_channels(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_row_sample(0, sample.id)
        logic.set_sample_subcolumn(0, pitch=Step(value=5))
        logic.set_sample_subcolumn(0, volume=10)

        logic.clear_sample_subcolumn(0, pitch=True)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            row = _row(controller, channel)
            assert row.pitch is None
            assert row.volume == 10
            assert row.command is not None


class TestAdjustTranspose:
    def test_first_nudge_writes_the_delta_from_zero(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.adjust_transpose(ChannelName.PULSE1, 0, 1)

        assert _row(controller, ChannelName.PULSE1).pitch == Step(value=1)

    def test_repeated_nudges_accumulate(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.adjust_transpose(ChannelName.PULSE1, 0, 1)
        logic.adjust_transpose(ChannelName.PULSE1, 0, 12)

        assert _row(controller, ChannelName.PULSE1).pitch == Step(value=13)

    def test_clamps_to_max_transpose(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, pitch=Step(value=MAX_TRANSPOSE))

        logic.adjust_transpose(ChannelName.PULSE1, 0, 12)

        assert _row(controller, ChannelName.PULSE1).pitch == Step(value=MAX_TRANSPOSE)

    def test_preserves_the_voice_and_the_volume(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="lead")
        _place_voice(controller, ChannelName.PULSE1, sample.id)
        logic.adjust_volume(ChannelName.PULSE1, 0, -1)

        logic.adjust_transpose(ChannelName.PULSE1, 0, 2)

        row = _row(controller, ChannelName.PULSE1)
        assert row.command is not None
        assert row.pitch == Step(value=2)
        assert row.volume == MAX_VOLUME - 1


class TestAdjustVolume:
    def test_unset_volume_steps_down_from_full(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.adjust_volume(ChannelName.PULSE1, 0, -1)

        assert _row(controller, ChannelName.PULSE1).volume == MAX_VOLUME - 1

    def test_unset_volume_up_stays_full(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.adjust_volume(ChannelName.PULSE1, 0, 1)

        assert _row(controller, ChannelName.PULSE1).volume == MAX_VOLUME

    def test_clamps_to_zero(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, volume=1)

        logic.adjust_volume(ChannelName.PULSE1, 0, -4)

        assert _row(controller, ChannelName.PULSE1).volume == 0


class TestBuildTrackerAggregation:
    def test_single_channel_of_a_multi_channel_sample_reads_mixed(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        _place_voice(controller, ChannelName.PULSE1, sample.id)

        row = logic.build_grid().rows[0]

        assert row.sample == MIXED

    def test_full_placement_reads_as_the_sample(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_row_sample(0, sample.id)

        row = logic.build_grid().rows[0]

        assert row.sample == row.cells[ChannelName.PULSE1].voice
        assert row.sample != MIXED

    def test_diverging_transpose_renders_as_mixed(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_row_sample(0, sample.id)
        logic.set_row(ChannelName.PULSE1, 0, pitch=Step(value=5))

        row = logic.build_grid().rows[0]

        assert row.transpose == MIXED

    def test_shared_transpose_is_reflected_in_the_sample_column(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_row_sample(0, sample.id)
        logic.set_sample_subcolumn(0, pitch=Step(value=5))

        row = logic.build_grid().rows[0]

        assert row.transpose == row.cells[ChannelName.PULSE1].transpose
        assert row.transpose != MIXED


class TestEmptyFrameAutoCreate:
    def _append_empty_frame(self, controller: ProjectController) -> None:
        controller.append_frame()

    def test_editing_an_empty_slot_creates_and_assigns_a_pattern(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        self._append_empty_frame(controller)
        logic.select_frame(1)

        logic.set_row(ChannelName.PULSE1, 0, pitch=Step(value=5))

        song = controller.project.song
        new_index = song.order[1][ChannelName.PULSE1]
        assert new_index is not None
        assert song[ChannelName.PULSE1].get_row(new_index, 0).pitch == Step(value=5)
        assert song.order[1][ChannelName.PULSE2] is None

    def test_empty_frame_still_shows_editable_rows(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        self._append_empty_frame(controller)
        logic.select_frame(1)

        tracker = logic.build_grid()

        assert len(tracker.rows) == controller.project.song.rows_per_pattern


class TestWhatTheSampleColumnPlaces:
    """The column spreads a voice over the channels it covers, which a recording states for itself."""

    def test_a_sample_is_placed_across_the_channels_it_covers(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )

        logic.place_note(0, None, sample.id)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            assert isinstance(_row(controller, channel).command, NoteOn)

    def test_an_instrument_leaves_the_row_as_it_stands(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        instrument = controller.add_instrument(new_instrument("lead"))

        logic.place_note(0, None, instrument.id)

        for channel in ChannelName.items():
            assert _row(controller, channel).command is None

    def test_an_instrument_lands_on_the_channel_column_that_names_it(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        instrument = controller.add_instrument(new_instrument("lead"))

        logic.place_note(0, ChannelName.NOISE, instrument.id)

        command = _row(controller, ChannelName.NOISE).command
        assert isinstance(command, NoteOn)
        assert command.voice_id == instrument.id

    def test_the_column_answers_for_a_sample(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1]),
            name="lead",
        )

        assert logic.places_in_sample_column(sample.id) is True

    def test_the_column_stands_by_for_an_instrument(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        instrument = controller.add_instrument(new_instrument("lead"))

        assert logic.places_in_sample_column(instrument.id) is False

    def test_the_column_stands_by_for_a_voice_the_project_lost(self) -> None:
        logic = SequencerTrackerLogic(_controller())

        assert logic.places_in_sample_column(UNKNOWN_SAMPLE_ID) is False


class TestWhatTheSampleColumnReads:
    """The column summarizes what its own kind of voice put on the row."""

    def test_an_instrument_alone_leaves_the_column_empty(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        instrument = controller.add_instrument(new_instrument("lead"))
        _place_voice(controller, ChannelName.PULSE1, instrument.id)

        row = logic.build_grid().rows[0]

        assert row.sample == display_id(None)
        assert row.sample_channels == frozenset()

    def test_a_sample_beside_an_instrument_reads_as_that_sample(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        instrument = controller.add_instrument(new_instrument("pad"))
        logic.set_row_sample(0, sample.id)
        _place_voice(controller, ChannelName.NOISE, instrument.id)

        row = logic.build_grid().rows[0]

        assert row.sample == row.cells[ChannelName.PULSE1].voice
        assert row.sample != MIXED

    def test_a_row_cut_on_every_channel_still_reads_as_a_cut(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.cut_note(0, None)

        assert logic.build_grid().rows[0].sample == NOTE_OFF

    def test_a_cell_names_the_kind_of_the_voice_it_starts(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1]),
            name="lead",
        )
        instrument = controller.add_instrument(new_instrument("pad"))
        _place_voice(controller, ChannelName.PULSE1, sample.id)
        _place_voice(controller, ChannelName.NOISE, instrument.id)

        cells = logic.build_grid().rows[0].cells

        assert cells[ChannelName.PULSE1].kind is VoiceKind.SAMPLE
        assert cells[ChannelName.NOISE].kind is VoiceKind.INSTRUMENT
        assert cells[ChannelName.TRIANGLE].kind is None


class TestTheSampleColumnFollowsTheSampleInForce:
    """A pitch or a volume typed in the sample column reaches the channels a sample is playing on."""

    def test_a_volume_below_a_placed_sample_reaches_the_channels_it_plays(self, grid: Grid) -> None:
        fill_frame(
            grid.logic,
            (f"{LEAD} ... . | .. ... . | {LEAD} ... . | .. ... .",),
            voice_ids=grid.voice_ids,
        )

        grid.logic.write_cell(2, None, None, None, 10)

        assert render_frame(grid.logic) == (
            "00 ... . | .. ... . | 00 ... . | .. ... .",
            EMPTY,
            ".. ... A | .. ... . | .. ... A | .. ... .",
            EMPTY,
        )

    def test_a_channel_cut_since_the_sample_began_takes_nothing(self, grid: Grid) -> None:
        fill_frame(
            grid.logic,
            (
                f"{LEAD} ... . | .. ... . | {LEAD} ... . | .. ... .",
                ".. ... . | .. ... . | ~~ ... . | .. ... .",
            ),
            voice_ids=grid.voice_ids,
        )

        grid.logic.write_cell(2, None, None, Step(value=3), None)

        assert render_frame(grid.logic)[2] == ".. +03 . | .. ... . | .. ... . | .. ... ."

    def test_a_channel_now_carrying_an_instrument_takes_nothing(self, grid: Grid) -> None:
        fill_frame(
            grid.logic,
            (
                f"{LEAD} ... . | .. ... . | {LEAD} ... . | .. ... .",
                f".. ... . | .. ... . | {PAD} ... . | .. ... .",
            ),
            voice_ids=grid.voice_ids,
        )

        grid.logic.write_cell(2, None, None, None, 10)

        assert render_frame(grid.logic)[2] == ".. ... A | .. ... . | .. ... . | .. ... ."

    def test_a_row_where_no_sample_plays_writes_nothing_and_creates_no_pattern(self, grid: Grid) -> None:
        position = grid.controller.project.song.order_length()
        grid.controller.append_frame()
        grid.logic.select_frame(position)

        grid.logic.write_cell(0, None, None, 5, None)
        grid.logic.write_cell(0, None, None, None, 10)

        assert render_slots(grid.controller, position) == ".. .. .. .."

    def test_a_row_placing_a_sample_keeps_its_whole_span(self, grid: Grid) -> None:
        """The sample the row names decides, so its empty triangle cell takes the value and the
        second pulse, still playing a sample from above, keeps its own."""
        fill_frame(
            grid.logic,
            (
                f".. ... . | {BASS} ... . | .. ... . | .. ... .",
                f"{LEAD} ... . | .. ... . | .. ... . | .. ... .",
            ),
            voice_ids=grid.voice_ids,
        )

        grid.logic.write_cell(1, None, None, None, 10)

        assert render_frame(grid.logic)[1] == "00 ... A | .. ... . | .. ... A | .. ... ."

    def test_the_sample_in_force_starts_over_at_each_frame(self, grid: Grid) -> None:
        """The reading runs down one frame, so the next frame's first row carries no sample."""
        fill_frame(
            grid.logic,
            (f"{LEAD} ... . | .. ... . | {LEAD} ... . | .. ... .",),
            voice_ids=grid.voice_ids,
        )
        position = grid.controller.project.song.order_length()
        grid.controller.append_frame()
        grid.logic.select_frame(position)
        fill_frame(
            grid.logic,
            (EMPTY, EMPTY, EMPTY, ".. ... 5 | .. ... . | .. ... 5 | .. ... ."),
            voice_ids=grid.voice_ids,
        )

        grid.logic.write_cell(0, None, None, None, 10)

        assert render_frame(grid.logic)[0] == EMPTY


class TestTheSampleColumnReadsWhereItWrites(BaseTestSuite):
    """The grid summarizes the sample column over the channels an edit there reaches.

    Each frame is read row by row, so the cell a reader types into and the cells that value lands
    in stay one group whatever the frame holds.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        frame: Tuple[str, ...]

    test_cases = (
        TestCase(
            label="a sample playing down the frame",
            frame=(f"{LEAD} ... . | .. ... . | {LEAD} ... . | .. ... .",),
        ),
        TestCase(
            label="a channel cut and another taken by an instrument",
            frame=(
                f"{LEAD} ... . | {BASS} ... . | {LEAD} ... . | .. ... .",
                ".. ... . | .. ... . | ~~ ... . | .. ... .",
                f"{PAD} ... . | .. ... . | .. ... . | .. ... .",
            ),
        ),
        TestCase(
            label="a second sample placed below the first",
            frame=(
                f".. ... . | {BASS} ... . | .. ... . | .. ... .",
                f"{LEAD} ... . | .. ... . | .. ... . | .. ... .",
            ),
        ),
        TestCase(
            label="nothing playing beside values in the channel columns",
            frame=(
                ".. +02 . | .. ... 5 | .. ... . | .. ... .",
                f".. ... . | .. ... . | .. ... . | {PAD} ... .",
            ),
        ),
        TestCase(
            label="a sample the project no longer holds",
            frame=(f"{UNKNOWN_SAMPLE} ... . | .. ... . | .. ... . | .. ... .",),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_pitch_and_a_volume_are_read_where_they_are_written(
        self,
        grid: Grid,
        test_case: TestCase,
    ) -> None:
        fill_frame(grid.logic, test_case.frame, voice_ids=grid.voice_ids)

        rows = grid.logic.build_grid().rows

        for row in rows:
            assert frozenset(grid.logic.relevant_channels(row.index)) == row.offset_channels

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_voice_is_read_where_it_is_written(
        self,
        grid: Grid,
        test_case: TestCase,
    ) -> None:
        fill_frame(grid.logic, test_case.frame, voice_ids=grid.voice_ids)

        rows = grid.logic.build_grid().rows

        for row in rows:
            assert frozenset(grid.logic.note_channels(row.index)) == row.note_channels
