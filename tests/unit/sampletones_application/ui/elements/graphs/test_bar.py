from typing import Final, List, Optional, Tuple
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_application.ui.elements.graphs import bar as bar_module
from sampletones_application.ui.elements.graphs.bar import GUIBarGraph
from sampletones_application.ui.elements.graphs.layers.bar import BarLayer
from sampletones_application.utils.palette.colors.literal import LiteralColor

BAND_SHARE: Final[float] = 0.2
BAR_VALUES: Final[Tuple[int, ...]] = (5, 9, 12, 3)
BAR_WEIGHT: Final[float] = 0.8
DATA_RANGE: Final[Tuple[int, int]] = (0, 15)
HOVER_TAG: Final[str] = "bar.hover"
LAYER_NAME: Final[str] = "volume"
PLOT_RANGE: Final[Tuple[float, float]] = (-2.0, 17.0)
PLOT_TAG: Final[str] = "bar.plot"
PRESSED_BAR: Final[int] = 1
PRESSED_VALUE: Final[float] = 6.0


def _graph() -> GUIBarGraph:
    """A bar plot holding one dimension's values, built as the panel builds it."""
    graph = GUIBarGraph.__new__(GUIBarGraph)
    graph.plot_tag = PLOT_TAG
    graph.hover_bar_tag = HOVER_TAG
    graph.data_range = DATA_RANGE
    graph.y_axis_tag = "bar.y"
    graph.x_axis_tag = "bar.x"
    graph.x_range = (-0.5, float(len(BAR_VALUES)))
    graph.y_range = PLOT_RANGE
    graph._default_y_range = PLOT_RANGE
    graph.current_data = np.array(BAR_VALUES)
    graph.layers = {
        LAYER_NAME: BarLayer(
            data=np.array(BAR_VALUES),
            name=LAYER_NAME,
            color=LiteralColor(value=(255, 255, 255, 255)),
            bar_weight=BAR_WEIGHT,
        )
    }
    graph._draw_stroke = None
    graph.on_bar_point_clicked = None
    graph.on_bar_point_hovered = None
    return graph


def _reserve_band(graph: GUIBarGraph, share: float) -> Tuple[float, float]:
    """The band the plot keeps beneath its bars, with the axes it locks left to DearPyGui."""
    with (
        patch.object(bar_module.dpg, "set_axis_limits"),
        patch.object(bar_module.dpg, "set_axis_limits_constraints"),
    ):
        return graph.reserve_band(share)


def _press(
    graph: GUIBarGraph,
    monkeypatch: pytest.MonkeyPatch,
    position: Tuple[float, float],
) -> None:
    """One frame of the left button held with the pointer standing at ``position`` in the plot.

    The plot's own items are DearPyGui's, so the reading answers that none of them is built and
    the case reads the values the press leaves behind.
    """
    monkeypatch.setattr(bar_module.dpg, "does_item_exist", lambda tag: False)
    monkeypatch.setattr(bar_module, "dpg_is_item_hovered", lambda tag: True)
    monkeypatch.setattr(bar_module, "dpg_configure_item", lambda tag, **kwargs: None)
    monkeypatch.setattr(bar_module.dpg, "is_key_down", lambda key: False)
    monkeypatch.setattr(bar_module.dpg, "get_plot_mouse_pos", lambda: position)
    monkeypatch.setattr(bar_module.dpg, "is_mouse_button_down", lambda button: True)
    monkeypatch.setattr(bar_module.dpg, "is_mouse_button_clicked", lambda button: False)
    graph._on_mouse_action(PLOT_TAG)


class TestPressingTheBars:
    """A press on the grid the bars stand on writes the value it lands at."""

    def test_a_press_writes_the_value_it_lands_at(self, monkeypatch: pytest.MonkeyPatch) -> None:
        graph = _graph()

        _press(graph, monkeypatch, (PRESSED_BAR + 0.5, PRESSED_VALUE))

        expected = list(BAR_VALUES)
        expected[PRESSED_BAR] = int(PRESSED_VALUE)
        assert list(graph.layers[LAYER_NAME].y_data) == expected


class TestPressingTheBandBeneathTheBars:
    """A band reserved beneath the bars reads which stretch belongs to whom.

    The band stands inside the plot the bars are drawn in, so a press meant for what it shows
    reaches the same handler; the values above it are the reader's and stay as they stand.
    """

    def test_a_press_inside_the_band_leaves_the_values_standing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        graph = _graph()
        band_low, band_high = _reserve_band(graph, BAND_SHARE)

        _press(graph, monkeypatch, (PRESSED_BAR + 0.5, (band_low + band_high) / 2))

        assert list(graph.layers[LAYER_NAME].y_data) == list(BAR_VALUES)

    def test_a_press_inside_the_band_still_reports_the_bar_it_stands_under(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        graph = _graph()
        band_low, band_high = _reserve_band(graph, BAND_SHARE)
        hovered: List[Tuple[Optional[str], Optional[int]]] = []
        graph.on_bar_point_hovered = lambda name, index: hovered.append((name, index))

        _press(graph, monkeypatch, (PRESSED_BAR + 0.5, (band_low + band_high) / 2))

        assert hovered == [(LAYER_NAME, PRESSED_BAR)]

    def test_a_press_above_the_band_writes_as_it_did_before_the_band(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Reserving a band lowers what the plot spans and leaves the bars every value they reach."""
        graph = _graph()
        _reserve_band(graph, BAND_SHARE)

        _press(graph, monkeypatch, (PRESSED_BAR + 0.5, PRESSED_VALUE))

        expected = list(BAR_VALUES)
        expected[PRESSED_BAR] = int(PRESSED_VALUE)
        assert list(graph.layers[LAYER_NAME].y_data) == expected
