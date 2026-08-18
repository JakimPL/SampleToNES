from tests.suite.surface import CLICKED_CELL, CLICKED_TARGET, CURSOR_TARGET, Grid


class TestTargetAtACell:
    def test_a_cell_is_paired_with_the_block_it_falls_in(self) -> None:
        assert Grid().cursor_targets().at(CLICKED_CELL) == CLICKED_TARGET

    def test_a_cell_away_from_the_cursor_names_its_own_block(self) -> None:
        """A menu raised anywhere reaches what it names, so the cursor's cell has no say in it."""
        assert Grid().cursor_targets().at(CLICKED_CELL) != CURSOR_TARGET


class TestTargetAtTheCursor:
    def test_the_cursor_names_its_own_target(self) -> None:
        assert Grid().cursor_targets().at_cursor() == CURSOR_TARGET

    def test_a_grid_holding_no_cursor_names_no_target(self) -> None:
        assert Grid(cursor=None).cursor_targets().at_cursor() is None

    def test_the_state_is_read_on_each_call(self) -> None:
        """A grid rebinds a frozen state on every edit, so a target resolved once would go stale."""
        grid = Grid()
        targets = grid.cursor_targets()
        first = targets.at_cursor()

        grid.cursor = CLICKED_CELL

        assert first == CURSOR_TARGET
        assert targets.at_cursor() == CLICKED_TARGET
