from typing import Any

import dearpygui.dearpygui as dpg

from sampletones.constants.enums import GeneratorName
from sampletones.constants.general import MAX_MIXER, MIXER
from sampletones.typehints import Sender, SerializedData

from ...config.manager import ConfigManager
from ...constants import (
    DIM_INPUT_WIDTH,
    DIM_PANEL_CONFIG_HEIGHT,
    FLAG_CHECKBOX_DEFAULT_ENABLED,
    LBL_CHECKBOX_NOISE,
    LBL_CHECKBOX_PULSE_1,
    LBL_CHECKBOX_PULSE_2,
    LBL_CHECKBOX_TRIANGLE,
    LBL_SECTION_RECONSTRUCTOR_GENERATOR_SELECTION,
    LBL_SECTION_RECONSTRUCTOR_SETTINGS,
    LBL_SLIDER_RECONSTRUCTOR_MIXER,
    LBL_TOOLTIP_RECONSTRUCTOR_MIXER,
    TAG_PANEL_MAIN_RECONSTRUCTOR_CELL,
    TAG_RECONSTRUCTOR_MIXER,
    TAG_RECONSTRUCTOR_PANEL,
    TPL_RECONSTRUCTION_GEN_TAG,
)
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.panel import GUIPanel
from ...utils.dpg import dpg_set_value
from ...utils.tooltip import show_tooltip


class GUIReconstructorPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager

        super().__init__(
            tag=TAG_RECONSTRUCTOR_PANEL,
            parent=TAG_PANEL_MAIN_RECONSTRUCTOR_CELL,
            height=DIM_PANEL_CONFIG_HEIGHT,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=True,
        ):
            self._create_section_text()
            self._create_generator_selection()
            self._create_mixer_slider()
            self._create_tooltips()

        self._register_callbacks()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_SECTION_RECONSTRUCTOR_SETTINGS)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_generator_selection(self) -> None:
        dpg.add_separator()
        dpg.add_text(LBL_SECTION_RECONSTRUCTOR_GENERATOR_SELECTION)

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

    def _create_mixer_slider(self) -> None:
        dpg.add_separator()
        dpg.add_slider_float(
            label=LBL_SLIDER_RECONSTRUCTOR_MIXER,
            tag=TAG_RECONSTRUCTOR_MIXER,
            min_value=0.0,
            max_value=MAX_MIXER,
            default_value=MIXER,
            width=DIM_INPUT_WIDTH,
        )

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_RECONSTRUCTOR_MIXER, LBL_TOOLTIP_RECONSTRUCTOR_MIXER)

    def _register_callbacks(self) -> None:
        for tag in self.config_manager.config_parameters["reconstructor"].keys():
            dpg.set_item_callback(tag, self._on_parameter_change)

        for generator_tag in self.config_manager.generator_tags.keys():
            dpg.set_item_callback(generator_tag, self._on_generator_change)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

    def _on_generator_change(self, sender: Sender, app_data: bool) -> None:
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

    def _get_all_gui_values(self) -> SerializedData:
        gui_values = {}
        for tag in self.config_manager.config_parameters["reconstructor"].keys():
            gui_values[tag] = dpg.get_value(tag)

        for generator_tag in self.config_manager.generator_tags.keys():
            gui_values[generator_tag] = dpg.get_value(generator_tag)

        return gui_values

    def update_gui_from_config(self) -> None:
        if not self.config_manager.config:
            return

        config = self.config_manager.config
        for tag, info in self.config_manager.config_parameters["reconstructor"].items():
            section_name = info["section"]
            section = getattr(config, section_name)
            if hasattr(section, tag):
                dpg.set_value(tag, getattr(section, tag))

        for generator_tag, generator in self.config_manager.generator_tags.items():
            dpg_set_value(generator_tag, generator in config.generation.generators)
