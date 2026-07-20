from dataclasses import dataclass

import pytest

from sampletones_application.ui.elements.layout.responsive import (
    expanded_side_width,
    stacked_graph_height,
)


@dataclass(frozen=True)
class StackedHeightCase:
    label: str
    base_height: int
    viewport_height: int
    baseline_viewport_height: int
    graph_count: int
    max_stack_height: int
    expected: int


_STACKED_HEIGHT_CASES = [
    StackedHeightCase("fills_at_baseline", 292, 800, 800, 2, 1200, 292),
    StackedHeightCase("holds_base_below_baseline", 292, 640, 800, 2, 1200, 292),
    StackedHeightCase("shares_surplus_equally", 292, 1000, 800, 2, 1200, 392),
    StackedHeightCase("just_below_the_cap", 292, 1414, 800, 2, 1200, 599),
    StackedHeightCase("reaches_the_cap", 292, 1416, 800, 2, 1200, 600),
    StackedHeightCase("holds_the_cap_above_it", 292, 2200, 800, 2, 1200, 600),
    StackedHeightCase("three_graphs_share_surplus", 292, 1100, 800, 3, 1200, 392),
    StackedHeightCase("three_graphs_lower_cap", 292, 1124, 800, 3, 1200, 400),
]


@dataclass(frozen=True)
class SideWidthCase:
    label: str
    base_width: int
    viewport_width: int
    baseline_viewport_width: int
    side_panel_count: int
    center_weight: int
    expected: int


_SIDE_WIDTH_CASES = [
    SideWidthCase("holds_base_at_baseline", 300, 1280, 1280, 2, 2, 300),
    SideWidthCase("holds_base_below_baseline", 300, 1000, 1280, 2, 2, 300),
    SideWidthCase("single_side_takes_a_third", 300, 1580, 1280, 1, 2, 400),
    SideWidthCase("two_sides_split_after_centre", 300, 1600, 1280, 2, 2, 380),
    SideWidthCase("heavier_centre_narrows_sides", 300, 1600, 1280, 2, 4, 353),
]


class TestStackedGraphHeight:
    """``stacked_graph_height`` fills a vertical graph stack at the lowest-resolution baseline, then
    shares the taller viewport's surplus equally across the graphs until their combined height reaches
    the configured maximum, from where each graph holds at its per-graph cap."""

    @pytest.mark.parametrize("case", _STACKED_HEIGHT_CASES, ids=lambda case: case.label)
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
    def test_stays_within_base_and_combined_cap(self, viewport_height: int) -> None:
        """Across the whole viewport range each graph sits at or above its base height and the graphs
        together stay within the combined maximum."""
        graph_count = 2
        max_stack_height = 1200
        height = stacked_graph_height(292, viewport_height, 800, graph_count, max_stack_height)
        assert height >= 292
        assert height * graph_count <= max_stack_height


class TestExpandedSideWidth:
    """``expanded_side_width`` holds a fixed side column at its configured width up to the design
    baseline, then grants it one share of the wider viewport's surplus against the stretching centre
    column's ``center_weight`` shares."""

    @pytest.mark.parametrize("case", _SIDE_WIDTH_CASES, ids=lambda case: case.label)
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
