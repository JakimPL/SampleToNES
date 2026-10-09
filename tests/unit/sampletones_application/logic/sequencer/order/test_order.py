from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.order import SequencerOrderLogic
from sampletones_core.constants.enums import ChannelName


def _logic() -> SequencerOrderLogic:
    return SequencerOrderLogic(ProjectController(ProjectManager()))


def _order_column(logic: SequencerOrderLogic, channel: ChannelName) -> list:
    """Returns the list of pattern indices for ``channel`` across all order positions."""
    song = logic._controller.project.song
    return [frame[channel] for frame in song.order]


class TestOrderMutations:
    def test_set_order_entry_assigns_one_channel(self) -> None:
        logic = _logic()

        logic.set_order_entry(ChannelName.PULSE1, 0, 3)

        assert _order_column(logic, ChannelName.PULSE1) == [3]
        assert _order_column(logic, ChannelName.TRIANGLE) == [0]

    def test_set_master_entry_broadcasts_to_every_channel(self) -> None:
        logic = _logic()

        logic.set_master_entry(0, 4)

        for channel in ChannelName.items():
            assert _order_column(logic, channel) == [4]

    def test_set_order_entry_clears_one_channel_with_none(self) -> None:
        logic = _logic()

        logic.set_order_entry(ChannelName.PULSE1, 0, None)

        assert _order_column(logic, ChannelName.PULSE1) == [None]
        assert _order_column(logic, ChannelName.TRIANGLE) == [0]

    def test_set_master_entry_clears_every_channel_with_none(self) -> None:
        logic = _logic()

        logic.set_master_entry(0, None)

        for channel in ChannelName.items():
            assert _order_column(logic, channel) == [None]

    def test_remove_from_order_drops_the_frame(self) -> None:
        logic = _logic()
        logic.insert_frame(1)

        logic.remove_from_order(0)

        for channel in ChannelName.items():
            assert _order_column(logic, channel) == [None]


class TestEntryAccess:
    """The reading and writing seam a block gesture goes through, which is the table's own rule."""

    def test_write_entry_reaches_one_channel(self) -> None:
        logic = _logic()

        logic.write_entry(ChannelName.PULSE1, 0, 3)

        assert _order_column(logic, ChannelName.PULSE1) == [3]
        assert _order_column(logic, ChannelName.TRIANGLE) == [0]

    def test_write_entry_through_the_master_row_reaches_every_channel(self) -> None:
        logic = _logic()

        logic.write_entry(None, 0, 3)

        for channel in ChannelName.items():
            assert _order_column(logic, channel) == [3]

    def test_entry_reads_the_index_a_channel_plays(self) -> None:
        logic = _logic()
        logic.set_order_entry(ChannelName.NOISE, 0, 7)

        assert logic.entry(ChannelName.NOISE, 0) == 7

    def test_entry_past_the_last_frame_reads_as_silence(self) -> None:
        logic = _logic()

        assert logic.entry(ChannelName.NOISE, logic.position_count()) is None

    def test_append_frame_lengthens_the_order_by_one(self) -> None:
        logic = _logic()
        length = logic.position_count()

        logic.append_frame()

        assert logic.position_count() == length + 1
        for channel in ChannelName.items():
            assert logic.entry(channel, length) is None


class TestOrderFrameOps:
    def test_insert_frame_adds_empty_frame_at_position(self) -> None:
        logic = _logic()
        logic.set_order_entry(ChannelName.PULSE1, 0, 5)

        logic.insert_frame(0)

        assert _order_column(logic, ChannelName.PULSE1) == [None, 5]

    def test_duplicate_frame_repeats_the_same_pattern(self) -> None:
        logic = _logic()
        logic.set_order_entry(ChannelName.PULSE1, 0, 5)

        logic.duplicate_frame(0)

        assert _order_column(logic, ChannelName.PULSE1) == [5, 5]

    def test_clone_frame_gives_the_copy_its_own_pattern(self) -> None:
        logic = _logic()
        logic.set_order_entry(ChannelName.PULSE1, 0, 5)

        logic.clone_frame(0)

        source_index, clone_index = _order_column(logic, ChannelName.PULSE1)
        assert source_index == 5
        assert clone_index != 5

    def test_clear_frame_empties_every_channel(self) -> None:
        logic = _logic()
        logic.set_master_entry(0, 4)

        logic.clear_frame(0)

        for channel in ChannelName.items():
            assert _order_column(logic, channel) == [None]

    def test_move_frame_reorders(self) -> None:
        logic = _logic()
        logic.insert_frame(1)
        logic.set_order_entry(ChannelName.PULSE1, 0, 1)
        logic.set_order_entry(ChannelName.PULSE1, 1, 2)

        logic.move_frame(0, 1)

        assert _order_column(logic, ChannelName.PULSE1) == [2, 1]


class TestBuildOrder:
    def test_position_count_matches_order_length(self) -> None:
        logic = _logic()
        logic.insert_frame(1)

        view_model = logic.build_order()

        assert view_model.position_count == 2
        assert set(view_model.channels) == set(ChannelName.items())
        assert view_model.entry_label(ChannelName.PULSE1, 1) == view_model.master_label(1)
