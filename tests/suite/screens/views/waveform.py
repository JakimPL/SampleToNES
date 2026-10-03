from typing import Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import (
    SUF_GRAPH_PLOT,
    SUF_GRAPH_X_AXIS,
    SUF_GRAPH_Y_AXIS,
    SUF_WAVEFORM_OVERLAY,
    SUF_WAVEFORM_POSITION_INDICATOR,
)
from tests.suite.screens.dearpygui.bridge import ONE_FRAME, Bridge
from tests.suite.screens.dearpygui.geometry import Point, Rect
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.dearpygui.plots import settled_plot_pointer

LINE_SERIES_TYPE: Final[str] = "mvAppItemType::mvLineSeries"
FIRST_POINT: Final[int] = 0
Y_VALUES: Final[int] = 1
MIDDLE: Final[float] = 0.5
SETTLING_SECONDS: Final[float] = 10.0


class MissingPlotError(AssertionError):
    """Raised when a scenario reaches for a waveform the screen draws nowhere."""


class Waveform:
    """A waveform graph: where it stands, what it draws, and the cursor marking the sample that plays.

    Positions along the graph are read in samples, which is what the graph's x axis counts. A
    gesture names a point by the fraction of the plot's width it lies at, halfway down the plot.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        tag: str,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._tag = tag
        self.plot = compose_tag(tag, SUF_GRAPH_PLOT)
        self.x_axis = compose_tag(tag, SUF_GRAPH_X_AXIS)
        self.y_axis = compose_tag(tag, SUF_GRAPH_Y_AXIS)
        self.cursor_line = compose_tag(tag, SUF_WAVEFORM_POSITION_INDICATOR)
        self.overlay = compose_tag(tag, SUF_WAVEFORM_OVERLAY)

    def point(self, fraction: float) -> Point:
        """The viewport point ``fraction`` of the way across the plot, halfway down it."""
        box = self._box()
        return Point(x=round(box.x + box.width * fraction), y=round(box.y + box.height * MIDDLE))

    def sample_under(self, fraction: float) -> float:
        """Rests the pointer ``fraction`` of the way across the plot and reads the sample the plot puts under it.

        Raises:
            ExpectationError: If the plot never reports the pointer resting on it.
        """
        self._hand.move_to(self.point(fraction))
        sample, _ = settled_plot_pointer(self._bridge, self.plot, timeout=SETTLING_SECONDS)
        return sample

    def cursor(self) -> Optional[float]:
        """The sample the cursor marks, or ``None`` while no cursor stands on the plot."""
        return self._bridge.ask(lambda: read_cursor(self.cursor_line))

    def limits(self) -> Tuple[float, float]:
        """The first and the last sample the plot shows."""
        low, high = self._bridge.ask(lambda: dpg.get_axis_limits(self.x_axis))
        return float(low), float(high)

    def series(self) -> Tuple[str, ...]:
        """The tags of the lines the plot draws, in the order it draws them, the last on top."""

        def read() -> Tuple[str, ...]:
            return tuple(
                str(dpg.get_item_alias(child))
                for child in dpg.get_item_children(self.y_axis, 1)
                if dpg.get_item_info(child)["type"] == LINE_SERIES_TYPE
            )

        return self._bridge.ask(read)

    def series_tag(self, layer: str) -> str:
        """The tag of the line the plot draws for ``layer``."""
        return compose_tag(self.y_axis, layer)

    def drawn(self, layer: str) -> List[float]:
        """The heights the plot draws ``layer`` at, one per point along it."""
        return [float(value) for value in self._bridge.ask(lambda: dpg.get_value(self.series_tag(layer)))[Y_VALUES]]

    def zoom_in(self, fraction: float, notches: int) -> None:
        """Turns the wheel up ``notches`` notches ``fraction`` of the way across the plot, narrowing what it shows."""
        self._hand.wheel_at(self.point(fraction), -notches)

    def click(self, fraction: float) -> None:
        """Clicks the plot ``fraction`` of the way across it."""
        self._hand.click_at(self.point(fraction))

    def double_click(self, fraction: float) -> None:
        """Double-clicks the plot ``fraction`` of the way across it."""
        self._hand.double_click_at(self.point(fraction))

    def triple_click(self, fraction: float) -> None:
        """Triple-clicks the plot ``fraction`` of the way across it."""
        self._hand.triple_click_at(self.point(fraction))

    def drag(self, start: float, end: float) -> None:
        """Drags across the plot from ``start`` to ``end``, each a fraction of its width."""
        self._hand.drag(self.point(start), self.point(end))

    def _box(self) -> Rect:
        """The plot's box once it stands where it stood a frame before, as a layout settling after a load leaves it."""
        settled = self._bridge.expect(
            self._two_frames_of_box,
            lambda boxes: boxes[0] is not None and boxes[0] == boxes[1],
            description=f"the plot '{self.plot}' standing still",
            timeout=SETTLING_SECONDS,
        )[0]
        if settled is None:
            raise MissingPlotError(f"The plot '{self.plot}' reports no box")

        return settled

    def _two_frames_of_box(self) -> Tuple[Optional[Rect], Optional[Rect]]:
        first = self._bridge.ask(lambda: read_item(self.plot).rect)
        self._bridge.frames(ONE_FRAME)
        return first, self._bridge.ask(lambda: read_item(self.plot).rect)


def read_cursor(cursor_line: str) -> Optional[float]:
    """The sample ``cursor_line`` marks in this frame, or ``None`` while it stands hidden. Runs on the render thread."""
    if not read_item(cursor_line).shown:
        return None

    return float(dpg.get_value(cursor_line)[FIRST_POINT][FIRST_POINT])
