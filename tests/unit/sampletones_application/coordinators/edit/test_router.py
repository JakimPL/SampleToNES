from typing import List, Sequence

from sampletones_application.coordinators.edit.router import EditRouter


class FakeSurface:
    """A test double for a grid offering editing gestures on the cell it holds a cursor in."""

    def __init__(self, name: str, *, focused: bool) -> None:
        self.name = name
        self.focused = focused
        self.builds = 0

    def owns_edit_actions(self) -> bool:
        return self.focused

    def build_edit_actions(self) -> None:
        self.builds += 1


def _router(surfaces: Sequence[FakeSurface]) -> EditRouter:
    return EditRouter(surfaces=surfaces)


class TestFocusedSurface:
    """The menu states the actions of whoever holds the cursor when it is opened."""

    def test_the_focused_surface_states_its_actions(self) -> None:
        tracker = FakeSurface("tracker", focused=True)
        order = FakeSurface("order", focused=False)
        router = _router([tracker, order])

        assert router.build_menu_actions() is True
        assert (tracker.builds, order.builds) == (1, 0)

    def test_a_surface_left_behind_states_nothing(self) -> None:
        tracker = FakeSurface("tracker", focused=False)
        order = FakeSurface("order", focused=True)
        router = _router([tracker, order])

        router.build_menu_actions()

        assert (tracker.builds, order.builds) == (0, 1)

    def test_nothing_is_built_with_no_surface_focused(self) -> None:
        """A tab switch leaves both grids holding their cursors while neither owns the keys."""
        surfaces = [FakeSurface("tracker", focused=False), FakeSurface("order", focused=False)]
        router = _router(surfaces)

        assert router.build_menu_actions() is False
        assert [surface.builds for surface in surfaces] == [0, 0]

    def test_a_router_with_no_surface_reports_nothing_built(self) -> None:
        assert _router([]).build_menu_actions() is False

    def test_the_surface_is_resolved_on_each_call(self) -> None:
        """The router holds no target, so a cursor taken after it was built reaches the menu."""
        tracker = FakeSurface("tracker", focused=False)
        router = _router([tracker])

        first: List[bool] = [router.build_menu_actions()]
        tracker.focused = True
        first.append(router.build_menu_actions())

        assert first == [False, True]
        assert tracker.builds == 1
