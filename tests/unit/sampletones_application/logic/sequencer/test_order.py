from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.order import SequencerOrderLogic
from sampletones_core.constants.enums import GeneratorName


def _logic() -> SequencerOrderLogic:
    return SequencerOrderLogic(ProjectController(ProjectManager()))


def _order_column(logic: SequencerOrderLogic, generator: GeneratorName) -> list:
    """Returns the list of pattern indices for ``generator`` across all order positions."""
    song = logic._controller.project.song
    return [frame[generator] for frame in song.order]


class TestOrderMutations:
    def test_set_order_entry_assigns_one_channel(self) -> None:
        logic = _logic()

        logic.set_order_entry(GeneratorName.PULSE1, 0, 3)

        assert _order_column(logic, GeneratorName.PULSE1) == [3]
        assert _order_column(logic, GeneratorName.TRIANGLE) == [0]

    def test_set_master_entry_broadcasts_to_every_channel(self) -> None:
        logic = _logic()

        logic.set_master_entry(0, 4)

        for generator in GeneratorName.items():
            assert _order_column(logic, generator) == [4]

    def test_set_order_entry_clears_one_channel_with_none(self) -> None:
        logic = _logic()

        logic.set_order_entry(GeneratorName.PULSE1, 0, None)

        assert _order_column(logic, GeneratorName.PULSE1) == [None]
        assert _order_column(logic, GeneratorName.TRIANGLE) == [0]

    def test_set_master_entry_clears_every_channel_with_none(self) -> None:
        logic = _logic()

        logic.set_master_entry(0, None)

        for generator in GeneratorName.items():
            assert _order_column(logic, generator) == [None]

    def test_remove_from_order_drops_the_frame(self) -> None:
        logic = _logic()
        logic.insert_frame(1)

        logic.remove_from_order(0)

        for generator in GeneratorName.items():
            assert _order_column(logic, generator) == [None]


class TestOrderFrameOps:
    def test_insert_frame_adds_empty_frame_at_position(self) -> None:
        logic = _logic()
        logic.set_order_entry(GeneratorName.PULSE1, 0, 5)

        logic.insert_frame(0)

        assert _order_column(logic, GeneratorName.PULSE1) == [None, 5]

    def test_duplicate_frame_repeats_the_same_pattern(self) -> None:
        logic = _logic()
        logic.set_order_entry(GeneratorName.PULSE1, 0, 5)

        logic.duplicate_frame(0)

        assert _order_column(logic, GeneratorName.PULSE1) == [5, 5]

    def test_clone_frame_gives_the_copy_its_own_pattern(self) -> None:
        logic = _logic()
        logic.set_order_entry(GeneratorName.PULSE1, 0, 5)

        logic.clone_frame(0)

        source_index, clone_index = _order_column(logic, GeneratorName.PULSE1)
        assert source_index == 5
        assert clone_index != 5

    def test_clear_frame_empties_every_channel(self) -> None:
        logic = _logic()
        logic.set_master_entry(0, 4)

        logic.clear_frame(0)

        for generator in GeneratorName.items():
            assert _order_column(logic, generator) == [None]

    def test_move_frame_reorders(self) -> None:
        logic = _logic()
        logic.insert_frame(1)
        logic.set_order_entry(GeneratorName.PULSE1, 0, 1)
        logic.set_order_entry(GeneratorName.PULSE1, 1, 2)

        logic.move_frame(0, 1)

        assert _order_column(logic, GeneratorName.PULSE1) == [2, 1]


class TestBuildOrder:
    def test_position_count_matches_order_length(self) -> None:
        logic = _logic()
        logic.insert_frame(1)

        view_model = logic.build_order()

        assert view_model.position_count == 2
        assert set(view_model.channels) == set(GeneratorName.items())
        assert view_model.entry_label(GeneratorName.PULSE1, 1) == view_model.master_label(1)
