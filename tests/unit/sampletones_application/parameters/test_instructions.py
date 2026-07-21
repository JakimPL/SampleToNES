from sampletones_application.layout.config import LayoutConfig
from sampletones_application.parameters.instructions import InstructionsTabParameters


class TestInstructionsTabParametersFromConfig:
    """The Instructions tab view forwards its cohesive models whole, flattens both the shared
    column geometry and the stacked-graph geometry the responsive sink consumes, and narrows the
    choice panel's slice of the general layout to a pitch-stepper style."""

    def test_forwards_models_and_flattens_geometry(self, layout_config: LayoutConfig) -> None:
        params = InstructionsTabParameters.from_config(layout_config)

        assert params.baseline_viewport_height == layout_config.general.responsive.baseline_viewport_height
        assert params.max_stack_height == layout_config.general.responsive.max_stack_height
        assert params.base_graph_height == layout_config.graphs.dimensions.height
        assert params.right_column_width == layout_config.tabs.instructions.right_column.width
        assert params.right_column_height == layout_config.tabs.instructions.right_column.height
        assert params.instructions is layout_config.tabs.instructions
        assert params.graphs is layout_config.graphs
        assert params.table_colors is layout_config.general.colors.tables
        assert params.tables is layout_config.general.tables
        assert params.scheduling is layout_config.behavior.scheduling

    def test_tree_colors_take_the_library_header_accent(self, layout_config: LayoutConfig) -> None:
        params = InstructionsTabParameters.from_config(layout_config)

        assert params.tree_colors.accent == layout_config.general.colors.headers.library

    def test_pitch_stepper_style_is_narrowed_from_general(self, layout_config: LayoutConfig) -> None:
        params = InstructionsTabParameters.from_config(layout_config)

        assert params.pitch_stepper_style.dimensions is layout_config.general.pitch_stepper
        assert params.pitch_stepper_style.plus_minus is layout_config.general.plus_minus_buttons
        assert params.pitch_stepper_style.value_color == layout_config.general.colors.text.disabled
