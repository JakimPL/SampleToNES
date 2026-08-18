from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import pytest

from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.elements.table.selection import TableSelection
from sampletones_application.utils.gui.keyboard.modifiers import Modifier

Key = Tuple[int, int]

ORIGIN: Key = (2, 1)
REACHED: Key = (5, 3)
FORGOTTEN: Key = (9, 9)
WIDGETS: Dict[Key, int] = {ORIGIN: 101, REACHED: 202}


class _Grid:
    """A grid stating what its selection covers, and recording what was painted on it."""

    def __init__(self, covered: Set[Key]) -> None:
        self.covered = covered
        self.painted: List[Tuple[int, bool]] = []
        self.cell: Optional[Key] = REACHED

    def covers(self) -> FrozenSet[Key]:
        return frozenset(self.covered)


def _selection(
    monkeypatch: pytest.MonkeyPatch,
    covered: Set[Key],
) -> Tuple[TableSelection[Key], _Grid]:
    cells: EditableCells[Key] = EditableCells()
    for key, widget in WIDGETS.items():
        cells.register(key, widget)

    grid = _Grid(covered)
    monkeypatch.setattr(
        "sampletones_application.ui.elements.table.selection.dpg.set_value",
        lambda widget, value: grid.painted.append((widget, value)),
    )
    monkeypatch.setattr(
        "sampletones_application.ui.elements.table.drag.capture_modifiers",
        lambda: set(),
    )
    return (
        TableSelection(cells=cells, cell_at=lambda: grid.cell, covered=grid.covers),
        grid,
    )


def _drag_out(selection: TableSelection[Key], widget: int) -> None:
    """Carries a press out to another cell, which is what turns it into a drag."""
    selection.hold(widget)
    selection.hold(widget)


class TestRepaint:
    """A repaint reaches the cells whose membership changed, and leaves the rest standing."""

    def test_the_cells_now_covered_are_marked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selection, grid = _selection(monkeypatch, covered={ORIGIN})

        selection.repaint()

        assert grid.painted == [(WIDGETS[ORIGIN], True)]

    def test_a_cell_the_selection_has_left_is_released(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selection, grid = _selection(monkeypatch, covered={ORIGIN})
        selection.repaint()
        grid.painted.clear()

        grid.covered = {REACHED}
        selection.repaint()

        assert sorted(grid.painted) == [(WIDGETS[ORIGIN], False), (WIDGETS[REACHED], True)]

    def test_a_cell_standing_as_it_was_is_left_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selection, grid = _selection(monkeypatch, covered={ORIGIN})
        selection.repaint()
        grid.painted.clear()

        selection.repaint()

        assert grid.painted == []

    def test_a_cell_the_cache_forgot_is_passed_over(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A region names cells of the grid, so a repaint reaches those the cache holds a widget for."""
        selection, grid = _selection(monkeypatch, covered={FORGOTTEN})

        selection.repaint()

        assert grid.painted == []


class TestClick:
    """A click releases the cell DearPyGui toggled, and a drag takes the click that ends it."""

    def test_a_click_releases_the_selectable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selection, grid = _selection(monkeypatch, covered=set())

        claimed = selection.claims_click(WIDGETS[ORIGIN], ORIGIN)

        assert claimed is False
        assert grid.painted == [(WIDGETS[ORIGIN], False)]

    def test_a_clicked_cell_the_selection_covers_is_marked_again(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The click leaves the cell released, so the repaint after it states the membership again."""
        selection, grid = _selection(monkeypatch, covered={ORIGIN})
        selection.repaint()
        grid.painted.clear()

        selection.claims_click(WIDGETS[ORIGIN], ORIGIN)
        selection.repaint()

        assert grid.painted == [(WIDGETS[ORIGIN], False), (WIDGETS[ORIGIN], True)]

    def test_a_drag_takes_the_click_that_ends_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selection, grid = _selection(monkeypatch, covered={ORIGIN})
        _drag_out(selection, WIDGETS[ORIGIN])
        grid.painted.clear()

        claimed = selection.claims_click(WIDGETS[ORIGIN], ORIGIN)

        assert claimed is True
        assert grid.painted == [(WIDGETS[ORIGIN], False), (WIDGETS[ORIGIN], True)]

    def test_a_second_click_stands_on_its_own(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The drag ends with the click it was claimed by, so the click after it places a cursor."""
        selection, _ = _selection(monkeypatch, covered={ORIGIN})
        _drag_out(selection, WIDGETS[ORIGIN])
        selection.claims_click(WIDGETS[ORIGIN], ORIGIN)

        assert selection.claims_click(WIDGETS[ORIGIN], ORIGIN) is False


class TestGestureAndReset:
    """The gesture in hand and the selection painted are dropped by different callers."""

    def test_dropping_the_gesture_leaves_the_selection_painted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selection, grid = _selection(monkeypatch, covered={ORIGIN})
        _drag_out(selection, WIDGETS[ORIGIN])
        selection.repaint()
        grid.painted.clear()

        selection.drop_gesture()
        selection.repaint()

        assert selection.claims_click(WIDGETS[ORIGIN], ORIGIN) is False
        assert grid.painted == [(WIDGETS[ORIGIN], False)]

    def test_a_reset_forgets_what_stood_painted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A rebuilt table holds cells of its own, so the selection is marked onto them afresh."""
        selection, grid = _selection(monkeypatch, covered={ORIGIN})
        selection.repaint()
        grid.painted.clear()

        selection.reset()
        selection.repaint()

        assert grid.painted == [(WIDGETS[ORIGIN], True)]

    def test_a_reset_drops_the_gesture_in_hand(self, monkeypatch: pytest.MonkeyPatch) -> None:
        selection, _ = _selection(monkeypatch, covered=set())
        _drag_out(selection, WIDGETS[ORIGIN])

        selection.reset()

        assert selection.claims_click(WIDGETS[ORIGIN], ORIGIN) is False


def test_a_shift_press_carries_the_selection_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reach a hold reports is the drag's own, which the grid turns into its selection."""
    selection, grid = _selection(monkeypatch, covered=set())
    monkeypatch.setattr(
        "sampletones_application.ui.elements.table.drag.capture_modifiers",
        lambda: {Modifier.SHIFT},
    )

    selection.hold(WIDGETS[ORIGIN])
    reach = selection.hold(WIDGETS[ORIGIN])

    assert reach is not None
    assert (reach.origin, reach.reached, reach.extends) == (ORIGIN, grid.cell, True)
