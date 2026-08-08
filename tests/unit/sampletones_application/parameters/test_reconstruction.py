from sampletones_application.layout.config import LayoutConfig
from sampletones_application.parameters.reconstruction import ReconstructionTabParameters


class TestReconstructionTabParametersFromConfig:
    """The Reconstruction tab view forwards its cohesive models whole, flattens the per-tab right
    column geometry, and narrows the instruments panel's slice of the general layout to a
    pitch-stepper style plus the two extra fields the panel draws with."""

    def test_forwards_models_and_flattens_geometry(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        params = ReconstructionTabParameters.from_config(layout_config)

        assert params.right_column_width == layout_config.tabs.reconstruction.right_column.width
        assert params.right_column_height == layout_config.tabs.reconstruction.right_column.height
        assert params.graphs is layout_config.graphs
        assert params.copy_width == layout_config.general.buttons.copy_width
        assert params.feature_colors is layout_config.general.colors.features
        assert params.path_colors is layout_config.general.colors.paths
        assert params.path_status_color == layout_config.general.colors.text.disabled
        assert params.scheduling is layout_config.behavior.scheduling

    def test_tree_colors_take_the_reconstruction_header_accent(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        params = ReconstructionTabParameters.from_config(layout_config)

        assert params.tree_colors.accent == layout_config.general.colors.headers.reconstruction

    def test_pitch_stepper_style_is_narrowed_from_general(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        params = ReconstructionTabParameters.from_config(layout_config)

        assert params.pitch_stepper_style.dimensions is layout_config.general.pitch_stepper
        assert params.pitch_stepper_style.plus_minus is layout_config.general.plus_minus_buttons
        assert params.pitch_stepper_style.value_color == layout_config.general.colors.text.disabled
