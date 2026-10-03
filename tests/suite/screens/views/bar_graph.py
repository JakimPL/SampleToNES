from dataclasses import dataclass
from typing import Final, List, Tuple

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import SUF_GRAPH_PLOT
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.dearpygui.plots import settled_plot_pointer

NEAR: Final[float] = 0.25
FAR: Final[float] = 0.75
BAR_MIDDLE: Final[float] = 0.5
HOVER_SECONDS: Final[float] = 10.0


class MissingGraphError(AssertionError):
    """Raised when a scenario reaches for a bar graph the screen draws nowhere."""


@dataclass(frozen=True)
class PlotMapping:
    """How a plot lays its values across the screen, read off two points the pointer rested on.

    A plot draws its axes in straight lines, so two readings fix where any value lands.
    """

    screen: Tuple[Point, Point]
    plot: Tuple[Tuple[float, float], Tuple[float, float]]

    def point(self, x: float, y: float) -> Point:
        """The viewport point the plot draws the value ``(x, y)`` at."""
        (near_x, near_y), (far_x, far_y) = self.plot
        near, far = self.screen
        return Point(
            x=round(near.x + (x - near_x) * (far.x - near.x) / (far_x - near_x)),
            y=round(near.y + (y - near_y) * (far.y - near.y) / (far_y - near_y)),
        )


class BarGraph:
    """A graph of one envelope drawn as bars, one per item, which a press or a drag sets."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        tag: str,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.plot = compose_tag(tag, SUF_GRAPH_PLOT)

    def mapping(self) -> PlotMapping:
        """Rests the pointer at two points of the plot and reads the values the plot puts under them."""
        rect = self._bridge.ask(lambda: read_item(self.plot).rect)
        if rect is None:
            raise MissingGraphError(f"The plot '{self.plot}' reports no box")

        points = (
            Point(x=round(rect.x + rect.width * NEAR), y=round(rect.y + rect.height * NEAR)),
            Point(x=round(rect.x + rect.width * FAR), y=round(rect.y + rect.height * FAR)),
        )
        readings: List[Tuple[float, float]] = []
        for point in points:
            readings.append(self.value_under(point))

        return PlotMapping(screen=points, plot=(readings[0], readings[1]))

    def value_under(self, point: Point) -> Tuple[float, float]:
        """Rests the pointer at ``point`` and reads the value the plot puts under it."""
        self._hand.move_to(point)
        return settled_plot_pointer(self._bridge, self.plot, timeout=HOVER_SECONDS)

    def zoom_in(self, fraction: float, notches: int) -> None:
        """Turns the wheel up ``notches`` notches ``fraction`` of the way across the plot, widening each bar there."""
        rect = self._bridge.ask(lambda: read_item(self.plot).rect)
        if rect is None:
            raise MissingGraphError(f"The plot '{self.plot}' reports no box")

        self._hand.wheel_at(
            Point(x=round(rect.x + rect.width * fraction), y=round(rect.y + rect.height * BAR_MIDDLE)), -notches
        )

    def drag_across(
        self,
        first: int,
        last: int,
        *,
        value: float,
    ) -> None:
        """Drags along the height of ``value`` from the bar of item ``first`` to the bar of item ``last``."""
        mapping = self.mapping()
        self._hand.drag(mapping.point(first + BAR_MIDDLE, value), mapping.point(last + BAR_MIDDLE, value))

    def item_under(self, point: Point) -> Tuple[int, float]:
        """The item whose bar stands under ``point``, and the value the plot puts there."""
        x, y = self.value_under(point)
        return int(x), y

    def drag_item(
        self,
        index: int,
        *,
        start: float,
        end: float,
    ) -> Point:
        """Drags the bar of item ``index`` from the value ``start`` to ``end``, and returns where it let go."""
        mapping = self.mapping()
        release = mapping.point(index + BAR_MIDDLE, end)
        self._hand.drag(mapping.point(index + BAR_MIDDLE, start), release)
        return release
