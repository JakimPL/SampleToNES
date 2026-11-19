from typing import Final

import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.parameters.geometry import TabGeometry

SIDE_PANELS: Final[int] = 2
BASE_WIDTH: Final[int] = 300
SHARE: Final[int] = 40


class TestTabGeometryFromConfig:
    """The shared geometry core reads its six scalars from the storage paths the coordinators
    used to reach through, so the deep-path knowledge lives in one factory instead of four.
    """

    def test_flattens_the_geometry_paths(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        geometry = TabGeometry.from_config(layout_config)

        assert geometry.side_width == layout_config.general.columns.side.width
        assert geometry.side_height == layout_config.general.columns.side.height
        assert geometry.center_weight == layout_config.general.columns.center_weight
        assert geometry.baseline_viewport_width == layout_config.general.responsive.baseline_viewport_width
        assert geometry.rail_width == layout_config.general.collapse.rail_width
        assert geometry.panel_gap == layout_config.general.panel_gap


class TestTheWidthASideColumnTakes:
    """A side column docks to the rail while its card is collapsed, holds its base width up to the
    design baseline, and widens by one share of the surplus past it."""

    @pytest.fixture(name="geometry")
    def geometry_fixture(self, layout_config: LayoutConfig) -> TabGeometry:
        return TabGeometry.from_config(layout_config)

    @pytest.mark.parametrize("surplus", [0, 1000, -500])
    def test_a_collapsed_column_takes_the_rail_whatever_the_viewport(self, geometry: TabGeometry, surplus: int) -> None:
        width = geometry.side_column_width(
            collapsed=True,
            base_width=geometry.side_width,
            side_panel_count=SIDE_PANELS,
            viewport_width=geometry.baseline_viewport_width + surplus,
        )
        assert width == geometry.rail_width

    @pytest.mark.parametrize("surplus", [0, -1, -800])
    def test_a_viewport_at_or_below_the_baseline_leaves_the_base_width(
        self, geometry: TabGeometry, surplus: int
    ) -> None:
        width = geometry.side_column_width(
            collapsed=False,
            base_width=BASE_WIDTH,
            side_panel_count=SIDE_PANELS,
            viewport_width=geometry.baseline_viewport_width + surplus,
        )
        assert width == BASE_WIDTH

    def test_a_wider_viewport_widens_the_column_by_one_share_of_the_surplus(self, geometry: TabGeometry) -> None:
        surplus = (geometry.center_weight + SIDE_PANELS) * SHARE
        width = geometry.side_column_width(
            collapsed=False,
            base_width=BASE_WIDTH,
            side_panel_count=SIDE_PANELS,
            viewport_width=geometry.baseline_viewport_width + surplus,
        )
        assert width == BASE_WIDTH + SHARE

    def test_more_side_columns_each_take_a_smaller_share(self, geometry: TabGeometry) -> None:
        widths = [
            geometry.side_column_width(
                collapsed=False,
                base_width=BASE_WIDTH,
                side_panel_count=count,
                viewport_width=geometry.baseline_viewport_width + 1200,
            )
            for count in (1, 2)
        ]
        assert widths[0] > widths[1] >= BASE_WIDTH
