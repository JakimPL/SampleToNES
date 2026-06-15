from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.order import SequencerOrderLogic
from sampletones_core.constants.enums import GeneratorName


def _logic() -> SequencerOrderLogic:
    return SequencerOrderLogic(ProjectController(ProjectManager()))


def _order(logic: SequencerOrderLogic, generator: GeneratorName) -> list:
    return logic._controller.project.song[generator].order


class TestOrderMutations:
    def test_set_order_entry_assigns_one_channel(self) -> None:
        logic = _logic()

        logic.set_order_entry(GeneratorName.PULSE1, 0, 3)

        assert _order(logic, GeneratorName.PULSE1) == [3]
        assert _order(logic, GeneratorName.TRIANGLE) == [0]

    def test_set_master_entry_broadcasts_to_every_channel(self) -> None:
        logic = _logic()

        logic.set_master_entry(0, 4)

        for generator in GeneratorName.items():
            assert _order(logic, generator) == [4]

    def test_set_order_entry_clears_one_channel_with_none(self) -> None:
        logic = _logic()

        logic.set_order_entry(GeneratorName.PULSE1, 0, None)

        assert _order(logic, GeneratorName.PULSE1) == [None]
        assert _order(logic, GeneratorName.TRIANGLE) == [0]

    def test_set_master_entry_clears_every_channel_with_none(self) -> None:
        logic = _logic()

        logic.set_master_entry(0, None)

        for generator in GeneratorName.items():
            assert _order(logic, generator) == [None]

    def test_add_to_order_all_appends_an_empty_slot(self) -> None:
        logic = _logic()

        logic.add_to_order_all()

        for generator in GeneratorName.items():
            assert _order(logic, generator) == [0, None]

    def test_remove_from_order_all_drops_the_position_everywhere(self) -> None:
        logic = _logic()
        logic.add_to_order_all()

        logic.remove_from_order_all(0)

        for generator in GeneratorName.items():
            assert _order(logic, generator) == [None]


class TestBuildOrder:
    def test_position_count_is_the_longest_channel(self) -> None:
        logic = _logic()
        logic._controller.append_to_order(GeneratorName.PULSE1, None)

        view_model = logic.build_order()

        assert view_model.position_count == 2
        assert set(view_model.channels) == set(GeneratorName.items())
        assert view_model.entry_label(GeneratorName.PULSE1, 1) == view_model.master_label(1)
