from sampletones_application.layout.config import LayoutConfig
from sampletones_application.parameters.sequencer import SequencerTabParameters


class TestSequencerTabParametersFromConfig:
    """The Sequencer tab view forwards its own layout and the cohesive general-layout blocks its
    panels draw with, and flattens the right-column geometry plus the two heights the coordinator
    blends into the samples card's reserved footprint."""

    def test_forwards_models_and_flattens_geometry(self, layout_config: LayoutConfig) -> None:
        params = SequencerTabParameters.from_config(layout_config)

        assert params.right_column_width == layout_config.tabs.sequencer.right_column.width
        assert params.right_column_height == layout_config.tabs.sequencer.right_column.height
        assert params.history_height == layout_config.tabs.sequencer.history.height
        assert params.header_bar_height == layout_config.general.collapse.header_bar_height
        assert params.sequencer is layout_config.tabs.sequencer
        assert params.inputs is layout_config.general.inputs
        assert params.plus_minus is layout_config.general.plus_minus_buttons
        assert params.feature_colors is layout_config.general.colors.features
        assert params.scheduling is layout_config.behavior.scheduling

    def test_tree_colors_take_the_reconstruction_header_accent(self, layout_config: LayoutConfig) -> None:
        params = SequencerTabParameters.from_config(layout_config)

        assert params.tree_colors.accent == layout_config.general.colors.headers.reconstruction
