from typing import Set

import pytest

from sampletones_application.ui.elements.tree.expansion import RowExpansionMemory

READER_ROW: str = "panel.node_reader"
MODE_ROW: str = "panel.node_mode"
WAY_DOWN: str = "panel.node_way_down"


@pytest.fixture
def memory() -> RowExpansionMemory:
    return RowExpansionMemory(set())


class TestTheRowsAMemoryHolds:
    def test_a_memory_opens_holding_the_rows_a_session_left(self) -> None:
        memory = RowExpansionMemory({READER_ROW})

        assert memory.stands_open(READER_ROW)
        assert memory.rows == {READER_ROW}

    def test_a_row_no_hand_opened_stands_closed(self, memory: RowExpansionMemory) -> None:
        assert not memory.stands_open(READER_ROW)
        assert not memory

    def test_the_rows_a_save_writes_are_the_readers_alone(self, memory: RowExpansionMemory) -> None:
        """A save writes the shape the reader built, the mode's way down being its own to hold."""
        memory.remember(READER_ROW, expanded=True)
        memory.follow({MODE_ROW})

        assert memory.rows == {READER_ROW}
        assert memory.stands_open(MODE_ROW)

    def test_the_rows_a_save_reads_are_taken_apart_from_the_memory(self, memory: RowExpansionMemory) -> None:
        memory.remember(READER_ROW, expanded=True)
        rows: Set[str] = memory.rows

        rows.add(MODE_ROW)

        assert memory.rows == {READER_ROW}


class TestFollowingTheReader:
    def test_a_row_the_reader_opens_is_theirs(self, memory: RowExpansionMemory) -> None:
        memory.remember(READER_ROW, expanded=True)

        assert memory.rows == {READER_ROW}

    def test_a_row_the_reader_folds_lets_go_of_the_modes_claim(self, memory: RowExpansionMemory) -> None:
        """A fold is the reader's word on a row whichever hand opened it, so the row stays folded."""
        memory.follow({MODE_ROW})

        memory.remember(MODE_ROW, expanded=False)

        assert not memory.stands_open(MODE_ROW)

    def test_a_row_the_reader_folds_leaves_the_shape_a_save_writes(self, memory: RowExpansionMemory) -> None:
        memory.remember(READER_ROW, expanded=True)

        memory.remember(READER_ROW, expanded=False)

        assert memory.rows == set()


class TestTheWayDownTheModeOpens:
    def test_the_way_down_stands_open_while_the_mode_does(self, memory: RowExpansionMemory) -> None:
        memory.follow({WAY_DOWN, MODE_ROW})

        assert memory.follows_the_mode
        assert memory.stands_open(WAY_DOWN)

    def test_a_release_folds_the_rows_the_mode_opened(self, memory: RowExpansionMemory) -> None:
        memory.follow({WAY_DOWN, MODE_ROW})

        memory.release(set())

        assert not memory.follows_the_mode
        assert not memory.stands_open(WAY_DOWN)

    def test_a_release_keeps_the_rows_the_readers_own_stand_on(self, memory: RowExpansionMemory) -> None:
        """A row of the mode's holding one of the reader's below it becomes theirs to keep."""
        memory.follow({WAY_DOWN, MODE_ROW})

        memory.release({WAY_DOWN})

        assert memory.rows == {WAY_DOWN}
        assert not memory.stands_open(MODE_ROW)

    def test_a_release_answers_for_the_rows_the_mode_opened_alone(self, memory: RowExpansionMemory) -> None:
        """The ways down a release is handed are read off the model, and a row no hand opened stays shut."""
        memory.follow({MODE_ROW})

        memory.release({WAY_DOWN})

        assert memory.rows == set()
        assert not memory.stands_open(WAY_DOWN)


class TestTheRowsTheModelStates:
    def test_a_row_the_model_dropped_leaves_both_memories(self, memory: RowExpansionMemory) -> None:
        memory.remember(READER_ROW, expanded=True)
        memory.follow({MODE_ROW})

        memory.hold_to({READER_ROW})

        assert memory.rows == {READER_ROW}
        assert not memory.stands_open(MODE_ROW)

    def test_holding_to_nothing_empties_the_memory(self, memory: RowExpansionMemory) -> None:
        memory.remember(READER_ROW, expanded=True)

        memory.hold_to(set())

        assert not memory
