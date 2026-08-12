from typing import Optional, Tuple

import pytest

from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.elements.table.drag import DragSelection
from sampletones_application.utils.gui.keyboard.modifiers import Modifier

Key = Tuple[int, int]

ORIGIN_WIDGET = 101
OTHER_WIDGET = 202
ORIGIN: Key = (2, 1)
REACHED: Key = (5, 3)


class _Pointer:
    """Where the pointer stands, which a drag reads off the grid between holds."""

    def __init__(self, cell: Optional[Key]) -> None:
        self.cell = cell


def _hold_modifiers(monkeypatch: pytest.MonkeyPatch, shift: bool) -> None:
    monkeypatch.setattr(
        "sampletones_application.ui.elements.table.drag.capture_modifiers",
        lambda: {Modifier.SHIFT} if shift else set(),
    )


def _drag(
    monkeypatch: pytest.MonkeyPatch,
    reached: Optional[Key],
    shift: bool = False,
) -> Tuple[DragSelection[Key], _Pointer]:
    cells: EditableCells[Key] = EditableCells()
    cells.register(ORIGIN, ORIGIN_WIDGET)
    pointer = _Pointer(reached)
    _hold_modifiers(monkeypatch, shift)
    return (
        DragSelection(cells=cells, cell_at=lambda: pointer.cell),
        pointer,
    )


class TestDragReach:
    """A press grows into a drag only once the pointer has left the cell it landed on."""

    def test_a_press_alone_reaches_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=REACHED)

        assert drag.hold(ORIGIN_WIDGET) is None

    def test_a_press_held_on_its_own_cell_stays_a_click(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=ORIGIN)

        drag.hold(ORIGIN_WIDGET)

        assert drag.hold(ORIGIN_WIDGET) is None

    def test_a_drag_reports_the_cell_it_grew_from(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=REACHED)

        drag.hold(ORIGIN_WIDGET)
        reach = drag.hold(ORIGIN_WIDGET)

        assert reach is not None
        assert reach.origin == ORIGIN
        assert reach.reached == REACHED
        assert reach.extends is False

    def test_a_shift_press_reports_a_carried_selection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=REACHED, shift=True)

        drag.hold(ORIGIN_WIDGET)
        reach = drag.hold(ORIGIN_WIDGET)

        assert reach is not None
        assert reach.extends is True

    def test_a_drag_returning_to_its_origin_reaches_that_cell(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, pointer = _drag(monkeypatch, reached=REACHED)

        drag.hold(ORIGIN_WIDGET)
        drag.hold(ORIGIN_WIDGET)
        pointer.cell = ORIGIN
        reach = drag.hold(ORIGIN_WIDGET)

        assert reach is not None
        assert reach.reached == ORIGIN

    def test_a_pointer_off_the_grid_reaches_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=None)

        drag.hold(ORIGIN_WIDGET)

        assert drag.hold(ORIGIN_WIDGET) is None

    def test_a_press_on_a_cell_the_cache_forgot_starts_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=REACHED)

        drag.hold(OTHER_WIDGET)

        assert drag.hold(OTHER_WIDGET) is None


class TestDragClick:
    """The click a drag ends on belongs to the drag; every other click is a gesture of its own."""

    def test_a_click_without_a_press_stands_on_its_own(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=REACHED)

        assert drag.claims_click() is False

    def test_a_press_that_never_moved_leaves_its_click_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=ORIGIN)

        drag.hold(ORIGIN_WIDGET)

        assert drag.claims_click() is False

    def test_a_drag_takes_the_click_that_ends_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=REACHED)

        drag.hold(ORIGIN_WIDGET)
        drag.hold(ORIGIN_WIDGET)

        assert drag.claims_click() is True

    def test_the_claimed_click_ends_the_gesture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=REACHED)

        drag.hold(ORIGIN_WIDGET)
        drag.hold(ORIGIN_WIDGET)
        drag.claims_click()

        assert drag.claims_click() is False

    def test_a_cleared_gesture_starts_afresh(self, monkeypatch: pytest.MonkeyPatch) -> None:
        drag, _ = _drag(monkeypatch, reached=REACHED)

        drag.hold(ORIGIN_WIDGET)
        drag.hold(ORIGIN_WIDGET)
        drag.clear()

        assert drag.claims_click() is False
        assert drag.hold(ORIGIN_WIDGET) is None
