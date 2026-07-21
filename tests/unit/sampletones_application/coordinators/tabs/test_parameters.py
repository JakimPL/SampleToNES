import pytest

from sampletones_application.coordinators.tabs.parameters import MainTabParameters, TabGeometry
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import BEHAVIOR_DIRECTORY, LAYOUT_DIRECTORY, PALETTE_PATH
from sampletones_application.utils.palette import Palette


@pytest.fixture
def layout_config() -> LayoutConfig:
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, Palette.load(PALETTE_PATH))


class TestTabGeometryFromConfig:
    """The shared geometry core reads its six scalars from the storage paths the coordinators
    used to reach through, so the deep-path knowledge lives in one factory instead of four."""

    def test_flattens_the_geometry_paths(self, layout_config: LayoutConfig) -> None:
        geometry = TabGeometry.from_config(layout_config)

        assert geometry.side_width == layout_config.general.columns.side.width
        assert geometry.side_height == layout_config.general.columns.side.height
        assert geometry.center_weight == layout_config.general.columns.center_weight
        assert geometry.baseline_viewport_width == layout_config.general.responsive.baseline_viewport_width
        assert geometry.rail_width == layout_config.general.collapse.rail_width
        assert geometry.panel_gap == layout_config.general.panel_gap


class TestMainTabParametersFromConfig:
    """The Main tab view forwards cohesive feature models whole and flattens only the geometry the
    coordinator feeds to pure-int sinks; the tree colors are pre-built at the composition root."""

    def test_forwards_models_and_flattens_geometry(self, layout_config: LayoutConfig) -> None:
        params = MainTabParameters.from_config(layout_config)

        assert params.config_height == layout_config.tabs.main.config.height
        assert params.main is layout_config.tabs.main
        assert params.inputs is layout_config.general.inputs
        assert params.path_colors is layout_config.general.colors.paths
        assert params.scheduling is layout_config.behavior.scheduling

    def test_tree_colors_take_the_path_hover_accent(self, layout_config: LayoutConfig) -> None:
        params = MainTabParameters.from_config(layout_config)

        assert params.tree_colors.accent == layout_config.general.colors.paths.hover
