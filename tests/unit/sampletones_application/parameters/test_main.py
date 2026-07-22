from sampletones_application.layout.config import LayoutConfig
from sampletones_application.parameters.main import MainTabParameters


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
