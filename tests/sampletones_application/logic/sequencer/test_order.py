from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.order import SequencerOrderLogic
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.patterns.row import Row


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

    def test_add_to_order_appends_an_empty_frame(self) -> None:
        logic = _logic()

        logic.add_to_order()

        for generator in GeneratorName.items():
            assert _order_column(logic, generator) == [0, None]

    def test_remove_from_order_drops_the_frame(self) -> None:
        logic = _logic()
        logic.add_to_order()

        logic.remove_from_order(0)

        for generator in GeneratorName.items():
            assert _order_column(logic, generator) == [None]


def _fill_all(logic: SequencerOrderLogic, position: int) -> None:
    """Writes an instrument to row 0 of every channel's pattern at the given order position."""
    song = logic._controller.project.song
    for generator in GeneratorName.items():
        index = song.order[position][generator]
        if index is None:
            index = song[generator].add_pattern(64)
            song.set_order_entry(position, generator, index)
        song[generator].patterns[index].rows[0] = Row(instrument=Instrument(sample_id="s", generator_name=generator))


def _assign_empty_pattern(logic: SequencerOrderLogic, position: int) -> None:
    """Assigns a fresh empty pattern to the given order position for every channel."""
    song = logic._controller.project.song
    for generator in GeneratorName.items():
        index = song[generator].add_pattern(64)
        logic.set_order_entry(generator, position, index)


class TestFindEmptyFrame:
    def test_fresh_project_has_no_empty_frame_after_position_zero(self) -> None:
        # Pressing "+" at frame 0: only the initial empty pattern at 0 exists,
        # which is at or before current — nothing to reuse, a new slot must be created.
        logic = _logic()

        result = logic.find_empty_frame(after=0)

        assert result is None

    def test_unassigned_slot_after_current_is_found(self) -> None:
        # Reuse scenario: a None slot exists ahead — navigate to it, don't add another.
        logic = _logic()
        logic.add_to_order()  # order = [0, None]

        result = logic.find_empty_frame(after=0)

        assert result == 1

    def test_unassigned_slot_at_or_before_current_is_not_found(self) -> None:
        # Pressing "+" while already at the unassigned slot: must create a new one ahead.
        logic = _logic()
        logic.add_to_order()  # order = [0, None], None is at position 1

        result = logic.find_empty_frame(after=1)

        assert result is None

    def test_second_consecutive_add_creates_new_slot_not_reuse_earlier_empty(self) -> None:
        # User presses "+" twice in a row: first goes to 1, second must go to 2.
        # Position 0 has an empty initial pattern but is behind current — must be ignored.
        logic = _logic()
        logic.add_to_order()  # order = [0, None], navigated to frame 1

        result = logic.find_empty_frame(after=1)  # current frame is now 1

        assert result is None  # no empty slot after frame 1 → new slot will be appended

    def test_empty_assigned_pattern_after_current_is_found(self) -> None:
        # Position 1 holds an assigned but fully empty pattern: pressing "+" from frame 0
        # should navigate there instead of appending yet another slot.
        logic = _logic()
        logic.add_to_order()
        _assign_empty_pattern(logic, 1)  # order = [0, <empty-pattern>]

        result = logic.find_empty_frame(after=0)

        assert result == 1

    def test_non_empty_pattern_after_current_is_not_found(self) -> None:
        logic = _logic()
        logic.add_to_order()
        _fill_all(logic, 1)  # order = [0, <filled>]

        result = logic.find_empty_frame(after=0)

        assert result is None

    def test_returns_first_empty_slot_when_multiple_exist_ahead(self) -> None:
        logic = _logic()
        logic.add_to_order()
        logic.add_to_order()  # order = [0, None, None]

        result = logic.find_empty_frame(after=0)

        assert result == 1

    def test_skips_to_second_empty_slot_when_first_is_current(self) -> None:
        logic = _logic()
        logic.add_to_order()
        logic.add_to_order()  # order = [0, None, None]

        result = logic.find_empty_frame(after=1)

        assert result == 2


class TestBuildOrder:
    def test_position_count_matches_order_length(self) -> None:
        logic = _logic()
        logic.add_to_order()

        view_model = logic.build_order()

        assert view_model.position_count == 2
        assert set(view_model.channels) == set(GeneratorName.items())
        assert view_model.entry_label(GeneratorName.PULSE1, 1) == view_model.master_label(1)
