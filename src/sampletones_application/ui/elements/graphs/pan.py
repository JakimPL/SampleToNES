from typing import Callable, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import SUF_HANDLER_WHEEL
from sampletones_application.utils.gui.dpg import dpg_is_item_hovered
from sampletones_application.utils.gui.keyboard.modifiers import Modifier, capture_modifiers
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

AxisLimits = Tuple[float, float]


class PlotWheelPan:
    """Pans a plot with the mouse wheel while Alt is held.

    Alt with the wheel moves the view along x, and Alt and Shift together move it along y, by
    ``pan_factor`` of the span in view for each notch. Scrolling down moves x toward larger values,
    the way a timeline advances, and scrolling up moves y toward larger values. A move stops at the
    bounds the graph constrains its axes to. The wheel acts while the pointer is over the plot or
    over any plot linked to it, such as the lanes standing beneath a waveform.

    The plot's own wheel zoom stays out of the way because the graph locks its axes while Alt is
    held, so the wheel reaches the view through this class alone.
    """

    def __init__(
        self,
        *,
        tag: str,
        plot_tags: Sequence[str],
        x_axis_tag: str,
        y_axis_tag: str,
        pan_factor: float,
        x_bounds: Callable[[], AxisLimits],
        y_bounds: Callable[[], AxisLimits],
        on_panned: VoidCallback,
    ) -> None:
        self._registry_tag = compose_tag(tag, SUF_HANDLER_WHEEL)
        self._plot_tags = tuple(plot_tags)
        self._x_axis_tag = x_axis_tag
        self._y_axis_tag = y_axis_tag
        self._pan_factor = pan_factor
        self._x_bounds = x_bounds
        self._y_bounds = y_bounds
        self._on_panned = on_panned

    def create(self) -> None:
        """Registers the wheel handler, which reads the pointer and the modifiers as each notch lands."""
        with dpg.handler_registry(tag=self._registry_tag):
            dpg.add_mouse_wheel_handler(callback=self._on_wheel)

    def _on_wheel(self, _sender: Sender, wheel: float) -> None:
        modifiers = capture_modifiers()
        if Modifier.ALT not in modifiers or not self._hovered():
            return

        if Modifier.SHIFT in modifiers:
            self._pan(self._y_axis_tag, self._y_bounds(), wheel)
        else:
            self._pan(self._x_axis_tag, self._x_bounds(), -wheel)

        self._on_panned()

    def _hovered(self) -> bool:
        return any(dpg_is_item_hovered(plot_tag) for plot_tag in self._plot_tags)

    def _pan(
        self,
        axis_tag: str,
        bounds: AxisLimits,
        notches: float,
    ) -> None:
        """Moves an axis by ``notches`` steps of the span in view, within ``bounds``."""
        low, high = dpg.get_axis_limits(axis_tag)
        span = high - low
        bound_low, bound_high = bounds
        if span >= bound_high - bound_low:
            return

        start = min(max(low + notches * self._pan_factor * span, bound_low), bound_high - span)
        dpg.set_axis_limits(axis_tag, start, start + span)
