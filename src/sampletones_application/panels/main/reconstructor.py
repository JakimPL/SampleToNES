from typing import Any

import dearpygui.dearpygui as dpg

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_MIXER
from sampletones_shared.types.application import Sender

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...config.updates import GenerationSettingsUpdate
from ...constants.general import (
    DIM_INPUT_WIDTH,
    LBL_CHECKBOX_GLOBAL_NOISE,
    LBL_CHECKBOX_GLOBAL_PULSE_1,
    LBL_CHECKBOX_GLOBAL_PULSE_2,
    LBL_CHECKBOX_GLOBAL_TRIANGLE,
    MSG_STATUS_INPUT,
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
from ...elements.settings import GUISettingsPanel
from ...elements.status import GUIStatusBar
from ...utils.dpg import dpg_set_value
from ...utils.tooltip import show_tooltip


class GUIReconstructorPanel(GUISettingsPanel):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
    ) -> None:
        super().__init__(
            config_manager=config_manager,
            application_config_manager=application_config_manager,
            tag=TAG_PANEL_MAIN_RECONSTRUCTOR,
            parent=TAG_PANEL_MAIN_RECONSTRUCTOR_CELL,
            height=DIM_PANEL_HEIGHT_MAIN_CONFIG,
        )

    def create_panel(self) -> None:
        self._setup_handlers()
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

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
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

        dpg.bind_item_handler_registry(TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER, self._item_handler_tag)
        GUIStatusBar.bind_to_item(TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER, MSG_STATUS_INPUT)

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER, LBL_TOOLTIP_MAIN_RECONSTRUCTOR_MIXER)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        generators = [
            generator
            for generator in GeneratorName
            if dpg.get_value(TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR.format(generator.value))
        ]
        generation_update = GenerationSettingsUpdate(
            mixer=float(self._clamp_value(TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER)),
            generators=generators,
        )
        self.config_manager.apply_generation_settings(generation_update)

    def update_gui_from_config(self) -> None:
        config = self.config_manager.config
        dpg.set_value(TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER, config.generation.mixer)
        for generator in GeneratorName:
            tag = TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR.format(generator.value)
            dpg_set_value(tag, generator in config.generation.generators)
