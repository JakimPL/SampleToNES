from dataclasses import dataclass

import pytest

from sampletones_application.ui.elements.layout.responsive import (
    expanded_side_width,
    stacked_graph_height,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


@dataclass(frozen=True)
class StackedHeightCase:
    label: str
    base_height: int
    viewport_height: int
    baseline_viewport_height: int
    graph_count: int
    max_stack_height: int
    expected: int


@dataclass(frozen=True)
class SideWidthCase:
    label: str
    base_width: int
    viewport_width: int
    baseline_viewport_width: int
    side_panel_count: int
    center_weight: int
    expected: int


class TestStackedGraphHeight(BaseTestSuite):
    """``stacked_graph_height`` fills a vertical graph stack at the lowest-resolution baseline, then
    shares the taller viewport's surplus equally across the graphs until their combined height reaches
    the configured maximum, from where each graph holds at its per-graph cap."""

    @dataclass(frozen=True, kw_only=True)
    class StackedHeightCase(BaseRegularTestCase):
        base_height: int
        viewport_height: int
        baseline_viewport_height: int
        graph_count: int
        max_stack_height: int
        expected: int

    test_cases = (
        StackedHeightCase(
            label="fills_at_baseline",
            base_height=292,
            viewport_height=800,
            baseline_viewport_height=800,
            graph_count=2,
            max_stack_height=1200,
            expected=292,
        ),
        StackedHeightCase(
            label="holds_base_below_baseline",
            base_height=292,
            viewport_height=640,
            baseline_viewport_height=800,
            graph_count=2,
            max_stack_height=1200,
            expected=292,
        ),
        StackedHeightCase(
            label="shares_surplus_equally",
            base_height=292,
            viewport_height=1000,
            baseline_viewport_height=800,
            graph_count=2,
            max_stack_height=1200,
            expected=392,
        ),
        StackedHeightCase(
            label="just_below_the_cap",
            base_height=292,
            viewport_height=1414,
            baseline_viewport_height=800,
            graph_count=2,
            max_stack_height=1200,
            expected=599,
        ),
        StackedHeightCase(
            label="reaches_the_cap",
            base_height=292,
            viewport_height=1416,
            baseline_viewport_height=800,
            graph_count=2,
            max_stack_height=1200,
            expected=600,
        ),
        StackedHeightCase(
            label="holds_the_cap_above_it",
            base_height=292,
            viewport_height=2200,
            baseline_viewport_height=800,
            graph_count=2,
            max_stack_height=1200,
            expected=600,
        ),
        StackedHeightCase(
            label="three_graphs_share_surplus",
            base_height=292,
            viewport_height=1100,
            baseline_viewport_height=800,
            graph_count=3,
            max_stack_height=1200,
            expected=392,
        ),
        StackedHeightCase(
            label="three_graphs_lower_cap",
            base_height=292,
            viewport_height=1124,
            baseline_viewport_height=800,
            graph_count=3,
            max_stack_height=1200,
            expected=400,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_height_follows_the_surplus_rule(self, case: StackedHeightCase) -> None:
        assert (
            stacked_graph_height(
                case.base_height,
                case.viewport_height,
                case.baseline_viewport_height,
                case.graph_count,
                case.max_stack_height,
            )
            == case.expected
        )

    @pytest.mark.parametrize("viewport_height", range(600, 3000, 37))
    def test_stays_within_base_and_combined_cap(
        self,
        viewport_height: int,
    ) -> None:
        """Across the whole viewport range each graph sits at or above its base height and the graphs
        together stay within the combined maximum."""
        graph_count = 2
        max_stack_height = 1200
        height = stacked_graph_height(292, viewport_height, 800, graph_count, max_stack_height)
        assert height >= 292
        assert height * graph_count <= max_stack_height


class TestExpandedSideWidth(BaseTestSuite):
    """``expanded_side_width`` holds a fixed side column at its configured width up to the design
    baseline, then grants it one share of the wider viewport's surplus against the stretching centre
    column's ``center_weight`` shares."""

    @dataclass(frozen=True, kw_only=True)
    class SideWidthCase(BaseRegularTestCase):
        base_width: int
        viewport_width: int
        baseline_viewport_width: int
        side_panel_count: int
        center_weight: int
        expected: int

    test_cases = (
        SideWidthCase(
            label="holds_base_at_baseline",
            base_width=300,
            viewport_width=1280,
            baseline_viewport_width=1280,
            side_panel_count=2,
            center_weight=2,
            expected=300,
        ),
        SideWidthCase(
            label="holds_base_below_baseline",
            base_width=300,
            viewport_width=1000,
            baseline_viewport_width=1280,
            side_panel_count=2,
            center_weight=2,
            expected=300,
        ),
        SideWidthCase(
            label="single_side_takes_a_third",
            base_width=300,
            viewport_width=1580,
            baseline_viewport_width=1280,
            side_panel_count=1,
            center_weight=2,
            expected=400,
        ),
        SideWidthCase(
            label="two_sides_split_after_centre",
            base_width=300,
            viewport_width=1600,
            baseline_viewport_width=1280,
            side_panel_count=2,
            center_weight=2,
            expected=380,
        ),
        SideWidthCase(
            label="heavier_centre_narrows_sides",
            base_width=300,
            viewport_width=1600,
            baseline_viewport_width=1280,
            side_panel_count=2,
            center_weight=4,
            expected=353,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_width_follows_the_surplus_split(self, case: SideWidthCase) -> None:
        assert (
            expanded_side_width(
                case.base_width,
                case.viewport_width,
                case.baseline_viewport_width,
                case.side_panel_count,
                case.center_weight,
            )
            == case.expected
        )
