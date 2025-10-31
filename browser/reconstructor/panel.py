import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.panel import GUIPanel
from constants.browser import (
    DIM_PANEL_RECONSTRUCTOR_HEIGHT,
    DIM_PANEL_RECONSTRUCTOR_WIDTH,
    FLAG_CHECKBOX_DEFAULT_ENABLED,
    LBL_CHECKBOX_NOISE,
    LBL_CHECKBOX_PULSE_1,
    LBL_CHECKBOX_PULSE_2,
    LBL_CHECKBOX_TRIANGLE,
    LBL_SECTION_GENERATOR_SELECTION,
    LBL_SECTION_RECONSTRUCTOR_SETTINGS,
    TAG_RECONSTRUCTOR_PANEL,
    TAG_RECONSTRUCTOR_PANEL_GROUP,
    TPL_RECONSTRUCTION_GEN_TAG,
)
from typehints.enums import GeneratorName


class GUIReconstructorPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager

        super().__init__(
            tag=TAG_RECONSTRUCTOR_PANEL,
            width=DIM_PANEL_RECONSTRUCTOR_WIDTH,
            height=DIM_PANEL_RECONSTRUCTOR_HEIGHT,
            parent_tag=TAG_RECONSTRUCTOR_PANEL_GROUP,
            init=True,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent_tag,
            width=self.width,
            height=self.height,
        ):
            dpg.add_text(LBL_SECTION_RECONSTRUCTOR_SETTINGS)
            dpg.add_separator()

            dpg.add_text(LBL_SECTION_GENERATOR_SELECTION)
            dpg.add_checkbox(
                label=LBL_CHECKBOX_PULSE_1,
                default_value=FLAG_CHECKBOX_DEFAULT_ENABLED,
                tag=TPL_RECONSTRUCTION_GEN_TAG.format(GeneratorName.PULSE1.value),
            )
            dpg.add_checkbox(
                label=LBL_CHECKBOX_PULSE_2,
                default_value=FLAG_CHECKBOX_DEFAULT_ENABLED,
                tag=TPL_RECONSTRUCTION_GEN_TAG.format(GeneratorName.PULSE2.value),
            )
            dpg.add_checkbox(
                label=LBL_CHECKBOX_TRIANGLE,
                default_value=FLAG_CHECKBOX_DEFAULT_ENABLED,
                tag=TPL_RECONSTRUCTION_GEN_TAG.format(GeneratorName.TRIANGLE.value),
            )
            dpg.add_checkbox(
                label=LBL_CHECKBOX_NOISE,
                default_value=FLAG_CHECKBOX_DEFAULT_ENABLED,
                tag=TPL_RECONSTRUCTION_GEN_TAG.format(GeneratorName.NOISE.value),
            )
