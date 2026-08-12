from dataclasses import dataclass
from typing import Callable, Final, Tuple

import pytest

from sampletones_application.ui.panels.sequencer.grid.surface.edit import GridEditSurface
from tests.suite.surface import CURSOR_CELL, CURSOR_TARGET, Grid, Target


@dataclass(frozen=True)
class GestureCase:
    """One of the four gestures as a key press raises it, at the cursor's own target."""

    name: str
    at_cursor: Callable[[GridEditSurface[str, str, str, Target]], None]
    reaches: str


CASES: Final[Tuple[GestureCase, ...]] = (
    GestureCase(
        name="copy",
        at_cursor=lambda surface: surface.copy(),
        reaches=f"copy {CURSOR_TARGET.region}",
    ),
    GestureCase(
        name="cut",
        at_cursor=lambda surface: surface.cut(),
        reaches=f"cut {CURSOR_TARGET.region}",
    ),
    GestureCase(
        name="delete",
        at_cursor=lambda surface: surface.delete(),
        reaches=f"delete {CURSOR_TARGET.region}",
    ),
    GestureCase(
        name="paste",
        at_cursor=lambda surface: surface.paste(),
        reaches=f"paste {CURSOR_TARGET.anchor}",
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
class TestAtTheCursor:
    """A key press acts on the target the cursor names, once the entry being typed has landed."""

    def test_a_gesture_reaches_the_cursor_s_own_target(self, case: GestureCase) -> None:
        grid = Grid()

        case.at_cursor(grid.edit_surface())

        assert grid.events == ["commit", case.reaches]

    def test_a_grid_holding_no_cursor_settles_its_entry_and_stands(self, case: GestureCase) -> None:
        grid = Grid(cursor=None)

        case.at_cursor(grid.edit_surface())

        assert grid.events == ["commit"]


class TestEditActions:
    def test_the_cursor_names_the_target_the_actions_are_built_for(self) -> None:
        grid = Grid()

        grid.edit_surface().build_edit_actions()

        assert grid.events == [f"actions {CURSOR_CELL}"]

    def test_a_grid_holding_no_cursor_builds_nothing(self) -> None:
        """The menu bar asks whichever grid answers, and one without a cursor states no actions."""
        grid = Grid(cursor=None)

        grid.edit_surface().build_edit_actions()

        assert grid.events == []

    def test_the_surface_answers_while_the_grid_owns_its_keys(self) -> None:
        """The menu offers what the next press would reach, so one question decides both."""
        assert Grid(owns=True).edit_surface().owns_edit_actions()
        assert not Grid(owns=False).edit_surface().owns_edit_actions()
