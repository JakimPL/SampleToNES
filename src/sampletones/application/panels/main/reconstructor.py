from typing import Any

import dearpygui.dearpygui as dpg

from sampletones.constants.enums import GeneratorName
from sampletones.constants.general import MAX_MIXER
from sampletones.typehints import Sender, SerializedData

from ...config.manager import ConfigManager
from ...constants.general import (
    DIM_INPUT_WIDTH,
    LBL_CHECKBOX_GLOBAL_NOISE,
    LBL_CHECKBOX_GLOBAL_PULSE_1,
    LBL_CHECKBOX_GLOBAL_PULSE_2,
    LBL_CHECKBOX_GLOBAL_TRIANGLE,
    MSG_STATUS_INPUT,
    SUF_HANDLER_REGISTRY,
)
from ...constants.main import (
    DIM_PANEL_HEIGHT_MAIN_CONFIG,
    LBL_SECTION_MAIN_RECONSTRUCTOR,
    LBL_SECTION_MAIN_RECONSTRUCTOR_SETTINGS,
    LBL_SLIDER_MAIN_RECONSTRUCTOR_MIXER,
    LBL_TOOLTIP_MAIN_RECONSTRUCTOR_MIXER,
    TAG_PANEL_MAIN_RECONSTRUCTOR,
    TAG_PANEL_MAIN_RECONSTRUCTOR_CELL,
    TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER,
    TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR,
)
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.panel import GUIPanel
from ...elements.status import GUIStatusBar
from ...utils.dpg import dpg_set_value
from ...utils.tooltip import show_tooltip


class GUIReconstructorPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager

        self._event_handler_tag = f"{TAG_PANEL_MAIN_RECONSTRUCTOR}{SUF_HANDLER_REGISTRY}"

        super().__init__(
            tag=TAG_PANEL_MAIN_RECONSTRUCTOR,
            parent=TAG_PANEL_MAIN_RECONSTRUCTOR_CELL,
            height=DIM_PANEL_HEIGHT_MAIN_CONFIG,
        )

    def create_panel(self) -> None:
        self._setup_event_handlers()
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

    def _setup_event_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._event_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_SECTION_MAIN_RECONSTRUCTOR_SETTINGS)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_generator_selection(self) -> None:
        dpg.add_separator()
        dpg.add_text(LBL_SECTION_MAIN_RECONSTRUCTOR)

        dpg.add_checkbox(
            label=LBL_CHECKBOX_GLOBAL_PULSE_1,
            default_value=GeneratorName.PULSE1 in self.config_manager.config.generation.generators,
            tag=TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR.format(GeneratorName.PULSE1.value),
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=LBL_CHECKBOX_GLOBAL_PULSE_2,
            default_value=GeneratorName.PULSE2 in self.config_manager.config.generation.generators,
            tag=TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR.format(GeneratorName.PULSE2.value),
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=LBL_CHECKBOX_GLOBAL_TRIANGLE,
            default_value=GeneratorName.TRIANGLE in self.config_manager.config.generation.generators,
            tag=TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR.format(GeneratorName.TRIANGLE.value),
            callback=self._on_parameter_change,
        )
        dpg.add_checkbox(
            label=LBL_CHECKBOX_GLOBAL_NOISE,
            default_value=GeneratorName.NOISE in self.config_manager.config.generation.generators,
            tag=TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR.format(GeneratorName.NOISE.value),
            callback=self._on_parameter_change,
        )

    def _create_mixer_slider(self) -> None:
        dpg.add_separator()
        dpg.add_slider_float(
            label=LBL_SLIDER_MAIN_RECONSTRUCTOR_MIXER,
            tag=TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER,
            min_value=0.0,
            max_value=MAX_MIXER,
            default_value=self.config_manager.config.generation.mixer,
            width=DIM_INPUT_WIDTH,
        )

        dpg.bind_item_handler_registry(TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER, self._event_handler_tag)
        GUIStatusBar.bind_to_item(TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER, MSG_STATUS_INPUT)

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER, LBL_TOOLTIP_MAIN_RECONSTRUCTOR_MIXER)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
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
            section_name = info.section
            section = getattr(config, section_name)
            if hasattr(section, info.name):
                dpg.set_value(tag, getattr(section, info.name))

        for generator_tag, generator in self.config_manager.generator_tags.items():
            dpg_set_value(generator_tag, generator in config.generation.generators)
