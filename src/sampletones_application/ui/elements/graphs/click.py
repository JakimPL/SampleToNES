import math
from dataclasses import dataclass
from typing import Callable, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.frame import FrameCallbackManager

# ImGui's io.MouseDoubleClickTime, which DearPyGui keeps at its default and exposes no setting for.
DOUBLE_CLICK_SECONDS: Final[float] = 0.30


@dataclass(frozen=True)
class PlotPress:
    """A left press on a plot: the sample under the pointer, where it went down, and when."""

    sample: float
    screen: Tuple[float, float]
    time: float


class PlotClickGesture:
    """Tells a click on a plot apart from the drag that pans it and the double-click that fits it.

    A press reads as a click when the pointer comes up within ``click_travel`` pixels of where it
    went down. A click is reported once it can no longer become the first half of a double-click:
    when the double-click window counted from its press has closed, or when the next press lands
    as a separate click. A press ImGui recognizes as the second half of a double-click is the one
    the plot fits its view on, so it takes the click before it along, and neither reports a sample.
    """

    def __init__(
        self,
        *,
        click_travel: float,
        on_clicked: Callable[[float], None],
    ) -> None:
        self._click_travel = click_travel
        self._on_clicked = on_clicked
        self._press: Optional[PlotPress] = None
        self._pending: Optional[PlotPress] = None

    def press(self) -> None:
        if dpg.is_mouse_button_double_clicked(dpg.mvMouseButton_Left):
            self._press = None
            self._pending = None
            return

        self._report_pending()
        sample, _ = dpg.get_plot_mouse_pos()
        screen_x, screen_y = dpg.get_mouse_pos(local=False)
        self._press = PlotPress(
            sample=sample,
            screen=(screen_x, screen_y),
            time=dpg.get_total_time(),
        )

    def release(self) -> None:
        press = self._press
        self._press = None
        if press is None or self._travel(press) > self._click_travel:
            return

        self._pending = press
        self._await_double_click_window()

    def _travel(self, press: PlotPress) -> float:
        screen_x, screen_y = dpg.get_mouse_pos(local=False)
        return math.hypot(screen_x - press.screen[0], screen_y - press.screen[1])

    def _await_double_click_window(self) -> None:
        pending = self._pending
        if pending is None:
            return

        if dpg.get_total_time() - pending.time < DOUBLE_CLICK_SECONDS:
            FrameCallbackManager.set_frame_callback(self._await_double_click_window)
            return

        self._report_pending()

    def _report_pending(self) -> None:
        pending = self._pending
        self._pending = None
        if pending is not None:
            self._on_clicked(pending.sample)
