from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_TRANSPOSE, MAX_VOLUME
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_shared.constants.symbols import MIXED
from tests.suite.sequencer import sample_reconstruction


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


def _place_instrument(
    controller: ProjectController,
    channel: ChannelName,
    sample_id: str,
) -> None:
    pattern_index = controller.project.song.order[0][channel]
    controller.set_row(
        channel,
        pattern_index,
        0,
        command=Instrument(sample_id=sample_id, channel_name=channel),
    )


class TestClearCell:
    def test_a_channel_cell_clears_only_that_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, transpose=5)
        logic.set_row(ChannelName.PULSE2, 0, transpose=7)

        logic.clear_cell(0, ChannelName.PULSE1)

        assert _row(controller, ChannelName.PULSE1).transpose is None
        assert _row(controller, ChannelName.PULSE2).transpose == 7

    def test_the_sample_column_clears_every_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_sample_subcolumn(0, transpose=5)

        logic.clear_cell(0, None)

        for channel in ChannelName.items():
            assert _row(controller, channel).transpose is None


class TestClearCellSubcolumn:
    def test_a_channel_cell_clears_one_subcolumn_of_its_own(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, transpose=5, volume=10)

        logic.clear_cell_subcolumn(0, ChannelName.PULSE1, SubColumn.TRANSPOSE)

        row = _row(controller, ChannelName.PULSE1)
        assert row.transpose is None
        assert row.volume == 10

    def test_the_sample_column_clears_instruments_from_every_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)
        logic.set_note_off(ChannelName.NOISE, 0)

        logic.clear_cell_subcolumn(0, None, SubColumn.INSTRUMENT)

        for channel in ChannelName.items():
            assert _row(controller, channel).command is None

    def test_the_sample_column_clears_transpose_from_the_sample_channels(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)
        for channel in ChannelName.items():
            logic.set_row(channel, 0, transpose=5)

        logic.clear_cell_subcolumn(0, None, SubColumn.TRANSPOSE)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            assert _row(controller, channel).transpose is None

        for channel in (ChannelName.PULSE2, ChannelName.NOISE):
            assert _row(controller, channel).transpose == 5


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
            assert isinstance(_row(controller, channel).command, Instrument)

        for channel in (ChannelName.PULSE2, ChannelName.NOISE):
            assert _row(controller, channel).command is None

    def test_a_sample_in_a_channel_cell_is_named_for_that_channel(self) -> None:
        """A cell re-targets the sample onto its own channel, whichever channels the sample covers."""
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1]),
            name="lead",
        )

        logic.write_cell(0, ChannelName.NOISE, sample.id, None, None)

        command = _row(controller, ChannelName.NOISE).command
        assert isinstance(command, Instrument)
        assert command.sample_id == sample.id
        assert command.channel_name == ChannelName.NOISE
        assert _row(controller, ChannelName.PULSE1).command is None

    def test_a_transpose_in_the_sample_column_reaches_every_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.write_cell(0, None, None, 5, None)

        for channel in ChannelName.items():
            assert _row(controller, channel).transpose == 5

    def test_a_volume_in_a_channel_cell_leaves_the_rest_of_the_cell_standing(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, transpose=5)

        logic.write_cell(0, ChannelName.PULSE1, None, None, 10)

        row = _row(controller, ChannelName.PULSE1)
        assert row.transpose == 5
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


class TestRowAccess:
    def test_reads_the_stored_row(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, transpose=5)

        row = logic.row(ChannelName.PULSE1, 0)

        assert row is not None
        assert row.transpose == 5

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
        _place_instrument(controller, ChannelName.PULSE1, sample.id)

        assert logic.referenced_channels(0) == frozenset(
            {
                ChannelName.PULSE1,
                ChannelName.TRIANGLE,
            }
        )

    def test_a_row_naming_no_sample_references_no_channel(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_note_off(ChannelName.PULSE1, 0)

        assert logic.referenced_channels(0) == frozenset()
        assert logic.relevant_channels(0) == ChannelName.items()


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

        logic.set_sample_instrument(0, sample.id)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            command = _row(controller, channel).command
            assert isinstance(command, Instrument)
            assert command.sample_id == sample.id
            assert command.channel_name == channel

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
            command=Instrument(
                sample_id=stale.id,
                channel_name=ChannelName.PULSE2,
            ),
            volume=15,
        )

        lead = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1]),
            name="lead",
        )
        logic.set_sample_instrument(0, lead.id)

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
        logic.set_sample_instrument(0, sample.id)

        logic.set_sample_instrument(0, None)

        for channel in ChannelName.items():
            assert _row(controller, channel).command is None


class TestSampleSubcolumn:
    def test_synchronises_across_relevant_channels_even_without_instrument(
        self,
    ) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        _place_instrument(controller, ChannelName.PULSE1, sample.id)

        logic.set_sample_subcolumn(0, transpose=5)
        logic.set_sample_subcolumn(0, volume=10)

        carrier = _row(controller, ChannelName.PULSE1)
        assert carrier.command is not None
        assert carrier.transpose == 5
        assert carrier.volume == 10

        synced = _row(controller, ChannelName.TRIANGLE)
        assert synced.command is None
        assert synced.transpose == 5
        assert synced.volume == 10

        for channel in (ChannelName.PULSE2, ChannelName.NOISE):
            row = _row(controller, channel)
            assert row.transpose is None
            assert row.volume is None

    def test_synchronises_across_all_channels_when_no_sample_is_referenced(
        self,
    ) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.set_sample_subcolumn(0, transpose=5, volume=10)

        for channel in ChannelName.items():
            row = _row(controller, channel)
            assert row.command is None
            assert row.transpose == 5
            assert row.volume == 10

    def test_clear_removes_one_subcolumn_across_relevant_channels(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)
        logic.set_sample_subcolumn(0, transpose=5)
        logic.set_sample_subcolumn(0, volume=10)

        logic.clear_sample_subcolumn(0, transpose=True)

        for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
            row = _row(controller, channel)
            assert row.transpose is None
            assert row.volume == 10
            assert row.command is not None


class TestAdjustTranspose:
    def test_first_nudge_writes_the_delta_from_zero(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.adjust_transpose(ChannelName.PULSE1, 0, 1)

        assert _row(controller, ChannelName.PULSE1).transpose == 1

    def test_repeated_nudges_accumulate(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)

        logic.adjust_transpose(ChannelName.PULSE1, 0, 1)
        logic.adjust_transpose(ChannelName.PULSE1, 0, 12)

        assert _row(controller, ChannelName.PULSE1).transpose == 13

    def test_clamps_to_max_transpose(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        logic.set_row(ChannelName.PULSE1, 0, transpose=MAX_TRANSPOSE)

        logic.adjust_transpose(ChannelName.PULSE1, 0, 12)

        assert _row(controller, ChannelName.PULSE1).transpose == MAX_TRANSPOSE

    def test_preserves_instrument_and_volume(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(sample_reconstruction([ChannelName.PULSE1]), name="lead")
        _place_instrument(controller, ChannelName.PULSE1, sample.id)
        logic.adjust_volume(ChannelName.PULSE1, 0, -1)

        logic.adjust_transpose(ChannelName.PULSE1, 0, 2)

        row = _row(controller, ChannelName.PULSE1)
        assert row.command is not None
        assert row.transpose == 2
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
        _place_instrument(controller, ChannelName.PULSE1, sample.id)

        row = logic.build_grid().rows[0]

        assert row.sample_instrument == MIXED

    def test_full_placement_reads_as_the_sample(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)

        row = logic.build_grid().rows[0]

        assert row.sample_instrument == row.cells[ChannelName.PULSE1].instrument
        assert row.sample_instrument != MIXED

    def test_diverging_transpose_renders_as_mixed(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)
        logic.set_row(ChannelName.PULSE1, 0, transpose=5)

        row = logic.build_grid().rows[0]

        assert row.sample_transpose == MIXED

    def test_shared_transpose_is_reflected_in_the_sample_column(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        sample = controller.add_sample(
            sample_reconstruction([ChannelName.PULSE1, ChannelName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)
        logic.set_sample_subcolumn(0, transpose=5)

        row = logic.build_grid().rows[0]

        assert row.sample_transpose == row.cells[ChannelName.PULSE1].transpose
        assert row.sample_transpose != MIXED


class TestEmptyFrameAutoCreate:
    def _append_empty_frame(self, controller: ProjectController) -> None:
        controller.append_frame()

    def test_editing_an_empty_slot_creates_and_assigns_a_pattern(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        self._append_empty_frame(controller)
        logic.select_frame(1)

        logic.set_row(ChannelName.PULSE1, 0, transpose=5)

        song = controller.project.song
        new_index = song.order[1][ChannelName.PULSE1]
        assert new_index is not None
        assert song[ChannelName.PULSE1].get_row(new_index, 0).transpose == 5
        assert song.order[1][ChannelName.PULSE2] is None

    def test_empty_frame_still_shows_editable_rows(self) -> None:
        controller = _controller()
        logic = SequencerTrackerLogic(controller)
        self._append_empty_frame(controller)
        logic.select_frame(1)

        tracker = logic.build_grid()

        assert len(tracker.rows) == controller.project.song.rows_per_pattern
