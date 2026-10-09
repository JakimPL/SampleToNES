from typing import Dict, FrozenSet, List, Tuple
from unittest.mock import patch

import pytest

from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.ui.elements.graphs import pan as pan_module
from sampletones_application.ui.elements.graphs.pan import PlotWheelPan
from sampletones_application.utils.gui.keyboard.modifiers import (
    ALT,
    CTRL_ALT_SHIFT,
    NO_MODIFIERS,
    SHIFT,
    ModifierSet,
)

PLOT: str = "graph.plot"
LANE: str = "graph.lane"
X_AXIS: str = "graph.x"
Y_AXIS: str = "graph.y"
X_BOUNDS: Tuple[float, float] = (0.0, 1000.0)
Y_BOUNDS: Tuple[float, float] = (-1.0, 1.0)
ALT_SHIFT: ModifierSet = ALT | SHIFT


class Scene:
    """A plot standing at some limits, with the wheel handler its pan registered."""

    def __init__(
        self,
        pan_factor: float,
        *,
        limits: Dict[str, Tuple[float, float]],
    ) -> None:
        self.limits = dict(limits)
        self.hovered: FrozenSet[str] = frozenset({PLOT})
        self.modifiers: ModifierSet = NO_MODIFIERS
        self.panned: List[None] = []
        self.pan = PlotWheelPan(
            tag="graph",
            plot_tags=(PLOT, LANE),
            x_axis_tag=X_AXIS,
            y_axis_tag=Y_AXIS,
            pan_factor=pan_factor,
            x_bounds=lambda: X_BOUNDS,
            y_bounds=lambda: Y_BOUNDS,
            on_panned=lambda: self.panned.append(None),
        )

    def scroll(self, wheel: float) -> None:
        with (
            patch.object(pan_module, "capture_modifiers", return_value=self.modifiers),
            patch.object(pan_module, "dpg_is_item_hovered", side_effect=lambda tag: tag in self.hovered),
            patch.object(pan_module.dpg, "get_axis_limits", side_effect=lambda axis: self.limits[axis]),
            patch.object(pan_module.dpg, "set_axis_limits", side_effect=self._set_limits),
        ):
            self.pan._on_wheel(0, wheel)

    def _set_limits(self, axis: str, low: float, high: float) -> None:
        self.limits[axis] = (low, high)


@pytest.fixture
def scene(graphs_layout: GraphsLayout) -> Scene:
    return Scene(
        graphs_layout.waveform.pan_factor,
        limits={X_AXIS: (400.0, 500.0), Y_AXIS: (-0.5, 0.5)},
    )


class TestAltWithTheWheelPansAlongX:
    def test_scrolling_down_moves_the_view_toward_larger_values(
        self,
        scene: Scene,
        graphs_layout: GraphsLayout,
    ) -> None:
        scene.modifiers = ALT

        scene.scroll(-1.0)

        step = graphs_layout.waveform.pan_factor * 100.0
        assert scene.limits[X_AXIS] == pytest.approx((400.0 + step, 500.0 + step))

    def test_scrolling_up_moves_the_view_toward_smaller_values(
        self,
        scene: Scene,
        graphs_layout: GraphsLayout,
    ) -> None:
        scene.modifiers = ALT

        scene.scroll(1.0)

        step = graphs_layout.waveform.pan_factor * 100.0
        assert scene.limits[X_AXIS] == pytest.approx((400.0 - step, 500.0 - step))

    def test_a_move_keeps_the_span_in_view(self, scene: Scene) -> None:
        scene.modifiers = ALT

        scene.scroll(-3.0)

        low, high = scene.limits[X_AXIS]
        assert high - low == pytest.approx(100.0)

    def test_the_y_axis_stays_where_it_was(self, scene: Scene) -> None:
        scene.modifiers = ALT

        scene.scroll(-1.0)

        assert scene.limits[Y_AXIS] == (-0.5, 0.5)

    def test_the_graph_is_told_once_a_move_is_made(self, scene: Scene) -> None:
        scene.modifiers = ALT

        scene.scroll(-1.0)

        assert len(scene.panned) == 1


class TestAltAndShiftWithTheWheelPanAlongY:
    def test_scrolling_up_moves_the_view_toward_larger_values(
        self,
        scene: Scene,
        graphs_layout: GraphsLayout,
    ) -> None:
        scene.modifiers = ALT_SHIFT

        scene.scroll(1.0)

        step = graphs_layout.waveform.pan_factor * 1.0
        assert scene.limits[Y_AXIS] == pytest.approx((-0.5 + step, 0.5 + step))

    def test_the_x_axis_stays_where_it_was(self, scene: Scene) -> None:
        scene.modifiers = ALT_SHIFT

        scene.scroll(1.0)

        assert scene.limits[X_AXIS] == (400.0, 500.0)


class TestWhereTheWheelDoesNothing:
    @pytest.mark.parametrize(
        "modifiers",
        [NO_MODIFIERS, SHIFT, CTRL_ALT_SHIFT - ALT],
        ids=["bare", "shift", "no alt"],
    )
    def test_a_wheel_without_alt_leaves_the_view_to_the_plot(
        self,
        scene: Scene,
        modifiers: ModifierSet,
    ) -> None:
        scene.modifiers = modifiers

        scene.scroll(-1.0)

        assert scene.limits == {X_AXIS: (400.0, 500.0), Y_AXIS: (-0.5, 0.5)}
        assert not scene.panned

    def test_a_wheel_away_from_the_plot_leaves_the_view_alone(self, scene: Scene) -> None:
        scene.modifiers = ALT
        scene.hovered = frozenset()

        scene.scroll(-1.0)

        assert scene.limits[X_AXIS] == (400.0, 500.0)
        assert not scene.panned

    def test_a_view_showing_the_whole_range_has_nowhere_to_go(self, scene: Scene) -> None:
        scene.modifiers = ALT
        scene.limits[X_AXIS] = X_BOUNDS

        scene.scroll(-1.0)

        assert scene.limits[X_AXIS] == X_BOUNDS


class TestPlotsLinkedToTheGraph:
    def test_the_wheel_over_a_linked_plot_pans_the_shared_axis(self, scene: Scene) -> None:
        scene.modifiers = ALT
        scene.hovered = frozenset({LANE})

        scene.scroll(-1.0)

        assert scene.limits[X_AXIS][0] > 400.0


class TestTheBoundsAMoveStopsAt:
    @pytest.mark.parametrize(
        ("limits", "wheel", "expected"),
        [
            ((990.0, 1000.0), -50.0, (990.0, 1000.0)),
            ((0.0, 10.0), 50.0, (0.0, 10.0)),
            ((980.0, 990.0), -50.0, (990.0, 1000.0)),
            ((10.0, 20.0), 50.0, (0.0, 10.0)),
        ],
        ids=["at the top", "at the bottom", "reaching the top", "reaching the bottom"],
    )
    def test_the_view_stops_at_the_edge_of_the_range(
        self,
        scene: Scene,
        limits: Tuple[float, float],
        wheel: float,
        expected: Tuple[float, float],
    ) -> None:
        scene.modifiers = ALT
        scene.limits[X_AXIS] = limits

        scene.scroll(wheel)

        assert scene.limits[X_AXIS] == pytest.approx(expected)


class TestRegisteringTheHandler:
    def test_the_wheel_handler_is_registered_under_the_graph(self, scene: Scene) -> None:
        with (
            patch.object(pan_module.dpg, "handler_registry") as registry,
            patch.object(pan_module.dpg, "add_mouse_wheel_handler") as handler,
        ):
            scene.pan.create()

        registry.assert_called_once()
        handler.assert_called_once_with(callback=scene.pan._on_wheel)
