from functools import partial
from typing import Tuple

import dearpygui.dearpygui as dpg

from automation.dearpygui.bridge import ONE_FRAME, Bridge

PlotValue = Tuple[float, float]


def read_plot_pointer() -> PlotValue:
    """The value the plot under the pointer puts there, as its last drawn frame read it."""
    x, y = dpg.get_plot_mouse_pos()
    return float(x), float(y)


def settled_plot_pointer(
    bridge: Bridge,
    plot: str,
    *,
    timeout: float,
) -> PlotValue:
    """The value ``plot`` puts under the resting pointer, once the plot holds it for two frames running.

    The plot reads the pointer as it draws, so its value trails the pointer by a frame.

    Raises:
        ExpectationError: If the pointer never rests on ``plot`` or its value keeps changing.
    """
    bridge.expect(
        lambda: bool(dpg.is_item_hovered(plot)),
        bool,
        description=f"the pointer resting on '{plot}'",
        timeout=timeout,
    )
    return bridge.expect(
        partial(_two_frames_of_pointer, bridge),
        lambda readings: readings[0] == readings[1],
        description=f"the value under the pointer on '{plot}' holding still",
        timeout=timeout,
    )[1]


def _two_frames_of_pointer(bridge: Bridge) -> Tuple[PlotValue, PlotValue]:
    first = bridge.ask(read_plot_pointer)
    bridge.frames(ONE_FRAME)
    return first, bridge.ask(read_plot_pointer)
