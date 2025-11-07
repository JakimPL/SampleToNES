from pathlib import Path
from typing import Any

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.panels.panel import GUIPanel
from constants.browser import (
    DIM_DIALOG_FILE_HEIGHT,
    DIM_DIALOG_FILE_WIDTH,
    DIM_PANEL_RECONSTRUCTOR_HEIGHT,
    DIM_PANEL_RECONSTRUCTOR_WIDTH,
    FLAG_CHECKBOX_DEFAULT_ENABLED,
    IDX_DIALOG_FIRST_SELECTION,
    KEY_DIALOG_SELECTIONS,
    LBL_BUTTON_SELECT_OUTPUT_DIRECTORY,
    LBL_CHECKBOX_NOISE,
    LBL_CHECKBOX_PULSE_1,
    LBL_CHECKBOX_PULSE_2,
    LBL_CHECKBOX_TRIANGLE,
    LBL_SECTION_GENERATOR_SELECTION,
    LBL_SECTION_OUTPUT_DIRECTORY,
    LBL_SECTION_RECONSTRUCTOR_SETTINGS,
    LBL_SLIDER_RECONSTRUCTOR_MIXER,
    LBL_SLIDER_RECONSTRUCTOR_TRANSFORMATION_GAMMA,
    TAG_OUTPUT_DIRECTORY_DISPLAY,
    TAG_RECONSTRUCTOR_MIXER,
    TAG_RECONSTRUCTOR_PANEL,
    TAG_RECONSTRUCTOR_PANEL_GROUP,
    TAG_RECONSTRUCTOR_TRANSFORMATION_GAMMA,
    TITLE_DIALOG_SELECT_OUTPUT_DIRECTORY,
    TPL_RECONSTRUCTION_GEN_TAG,
)
from constants.enums import GeneratorName
from constants.general import MAX_MIXER, MIXER, OUTPUT_DIRECTORY
from utils.serialization import SerializedData


class GUIReconstructorPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager

        super().__init__(
            tag=TAG_RECONSTRUCTOR_PANEL,
            width=DIM_PANEL_RECONSTRUCTOR_WIDTH,
            height=DIM_PANEL_RECONSTRUCTOR_HEIGHT,
            parent_tag=TAG_RECONSTRUCTOR_PANEL_GROUP,
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

            dpg.add_text(LBL_SECTION_OUTPUT_DIRECTORY)
            dpg.add_button(
                label=LBL_BUTTON_SELECT_OUTPUT_DIRECTORY,
                width=-1,
                callback=self._select_output_directory_dialog,
            )

            output_directory = (
                self.config_manager.config.general.output_directory if self.config_manager.config else OUTPUT_DIRECTORY
            )
            dpg.add_text(output_directory, tag=TAG_OUTPUT_DIRECTORY_DISPLAY)

            dpg.add_separator()

            dpg.add_text(LBL_SLIDER_RECONSTRUCTOR_MIXER)
            dpg.add_slider_float(
                min_value=0.0,
                max_value=MAX_MIXER,
                default_value=MIXER,
                width=-1,
                tag=TAG_RECONSTRUCTOR_MIXER,
            )
            dpg.add_text(LBL_SLIDER_RECONSTRUCTOR_TRANSFORMATION_GAMMA)
            dpg.add_slider_float(
                min_value=0.0,
                max_value=1.0,
                width=-1,
                tag=TAG_RECONSTRUCTOR_TRANSFORMATION_GAMMA,
            )
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

        self._register_callbacks()

    def _register_callbacks(self) -> None:
        for tag in self.config_manager.config_parameters["reconstructor"].keys():
            dpg.set_item_callback(tag, self._on_parameter_change)

        for generator_tag in self.config_manager.generator_tags.keys():
            dpg.set_item_callback(generator_tag, self._on_generator_change)

    def _on_parameter_change(self, sender: Any, app_data: Any) -> None:
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

    def _on_generator_change(self, sender: Any, app_data: bool) -> None:
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

    def _get_all_gui_values(self) -> SerializedData:
        gui_values = {}
        for tag in self.config_manager.config_parameters["reconstructor"].keys():
            gui_values[tag] = dpg.get_value(tag)

        for generator_tag in self.config_manager.generator_tags.keys():
            gui_values[generator_tag] = dpg.get_value(generator_tag)

        return gui_values

    def _select_output_directory_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_SELECT_OUTPUT_DIRECTORY,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._select_output_directory,
            directory_selector=True,
        ):
            pass

    def _select_output_directory(self, sender: Any, app_data: SerializedData) -> None:
        directory_path = list(app_data[KEY_DIALOG_SELECTIONS].values())[IDX_DIALOG_FIRST_SELECTION]
        self.change_output_directory(directory_path)

    def change_output_directory(self, directory_path: Path) -> None:
        self.config_manager.output_directory = directory_path
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)
        dpg.set_value(TAG_OUTPUT_DIRECTORY_DISPLAY, str(directory_path))

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
            dpg.set_value(generator_tag, generator in config.generation.generators)

        dpg.set_value(TAG_OUTPUT_DIRECTORY_DISPLAY, str(config.general.output_directory))
