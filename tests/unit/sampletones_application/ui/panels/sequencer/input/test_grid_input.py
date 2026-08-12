from dataclasses import dataclass

from sampletones_application.ui.panels.sequencer.input.state import GridInputState


@dataclass(frozen=True)
class _Cell:
    row: int
    column: int


@dataclass(frozen=True)
class _Block:
    first_row: int
    last_row: int
    first_column: int
    last_column: int


@dataclass(frozen=True)
class _GridState(GridInputState[_Cell, _Block]):
    """A grid of plain rows and columns, which is the coordinate space the shared rules are read in."""

    def _region_between(self, first: _Cell, second: _Cell) -> _Block:
        return _Block(
            first_row=min(first.row, second.row),
            last_row=max(first.row, second.row),
            first_column=min(first.column, second.column),
            last_column=max(first.column, second.column),
        )

    def _covers(self, region: _Block, cell: _Cell) -> bool:
        return (
            region.first_row <= cell.row <= region.last_row and region.first_column <= cell.column <= region.last_column
        )


def _state(
    row: int = 2,
    column: int = 1,
    pending: str = "",
) -> _GridState:
    return _GridState(cursor=_Cell(row, column), pending=pending)


class TestSelection:
    """A selection stands between the anchor a gesture started on and the cursor it carried to."""

    def test_a_cursor_alone_covers_no_region(self) -> None:
        assert _state().region is None

    def test_the_first_extend_anchors_the_cell_it_came_from(self) -> None:
        extended = _state(row=2, column=1).extend_to(_Cell(4, 3))

        assert extended.anchor == _Cell(2, 1)
        assert extended.region == _Block(first_row=2, last_row=4, first_column=1, last_column=3)

    def test_a_later_extend_keeps_the_anchor_it_began_on(self) -> None:
        extended = _state(row=2, column=1).extend_to(_Cell(4, 3)).extend_to(_Cell(6, 5))

        assert extended.anchor == _Cell(2, 1)
        assert extended.region == _Block(first_row=2, last_row=6, first_column=1, last_column=5)

    def test_extending_backwards_names_the_same_region_as_forwards(self) -> None:
        backwards = _state(row=4, column=3).extend_to(_Cell(2, 1)).region
        forwards = _state(row=2, column=1).extend_to(_Cell(4, 3)).region

        assert backwards == forwards

    def test_extending_leaves_nothing_pending(self) -> None:
        assert _state(pending="5").extend_to(_Cell(4, 3)).pending == ""

    def test_collapsing_drops_the_selection_and_holds_the_entry(self) -> None:
        collapsed = _GridState(cursor=_Cell(2, 1), pending="5", anchor=_Cell(4, 3)).collapse()

        assert collapsed.region is None
        assert collapsed.pending == "5"

    def test_dropping_a_partial_entry_holds_the_selection(self) -> None:
        held = _state(pending="5").extend_to(_Cell(4, 3)).reset_pending()

        assert held.region is not None
        assert held.pending == ""

    def test_cancel_drops_the_selection_and_the_partial_entry(self) -> None:
        cancelled = _GridState(cursor=_Cell(2, 1), pending="5", anchor=_Cell(4, 3)).cancel()

        assert cancelled.region is None
        assert cancelled.pending == ""
        assert cancelled.cursor == _Cell(2, 1)

    def test_a_committed_entry_leaves_the_cursor_alone(self) -> None:
        settled = _GridState(cursor=_Cell(2, 1), pending="5", anchor=_Cell(4, 3))._after_entry()

        assert settled.region is None
        assert settled.pending == ""

    def test_a_transition_answers_as_the_grid_it_came_from(self) -> None:
        """A grid state states its own rules, so what a shared rule builds is the grid's own state."""
        assert isinstance(_state().extend_to(_Cell(4, 3)), _GridState)
        assert isinstance(_state().reset_pending(), _GridState)
        assert isinstance(_state().collapse(), _GridState)
        assert isinstance(_state().select_between(_Cell(0, 0), _Cell(4, 3)), _GridState)


class TestSelectBetween:
    """A select gesture names a shape by its corners, which is how each grid states its own shapes."""

    def test_the_selection_covers_the_rectangle_the_two_cells_bound(self) -> None:
        selected = _state().select_between(_Cell(0, 0), _Cell(6, 5))

        assert selected.region == _Block(first_row=0, last_row=6, first_column=0, last_column=5)

    def test_the_cursor_lands_on_the_far_corner(self) -> None:
        """The next extending press then works from the edge the reader has just reached."""
        selected = _state().select_between(_Cell(0, 0), _Cell(6, 5))

        assert selected.anchor == _Cell(0, 0)
        assert selected.cursor == _Cell(6, 5)

    def test_a_shape_takes_over_from_the_selection_standing(self) -> None:
        held = _state().extend_to(_Cell(4, 3))

        selected = held.select_between(_Cell(0, 0), _Cell(6, 5))

        assert selected.region == _Block(first_row=0, last_row=6, first_column=0, last_column=5)

    def test_a_shape_settles_a_partial_entry(self) -> None:
        assert _state(pending="5").select_between(_Cell(0, 0), _Cell(6, 5)).pending == ""


class TestTarget:
    """The region a block gesture acts on, which is the selection wherever one has been made."""

    def test_a_cell_of_a_grid_with_nothing_selected_is_raised_on_itself(self) -> None:
        assert _state(row=2, column=1).region_at(_Cell(2, 1)) == _Block(
            first_row=2,
            last_row=2,
            first_column=1,
            last_column=1,
        )

    def test_a_cell_inside_the_selection_is_raised_on_the_whole_of_it(self) -> None:
        selected = _state(row=2, column=1).extend_to(_Cell(6, 5))

        assert selected.region_at(_Cell(4, 3)) == selected.region

    def test_a_cell_outside_the_selection_is_raised_on_itself(self) -> None:
        selected = _state(row=2, column=1).extend_to(_Cell(4, 3))

        assert selected.region_at(_Cell(8, 7)) == _Block(
            first_row=8,
            last_row=8,
            first_column=7,
            last_column=7,
        )
