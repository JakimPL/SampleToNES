import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import dearpygui.dearpygui as dpg
import numpy as np

from browser.config.manager import ConfigManager
from browser.config.panel import ConfigPanelGUI
from browser.constants import *
from browser.library.panel import LibraryPanelGUI
from reconstructor.reconstruction import Reconstruction
from reconstructor.reconstructor import Reconstructor
from typehints.general import GENERATOR_NAMES, GeneratorName
from utils.audioio import load_audio, play_audio, write_audio


class GUI:
    def __init__(self) -> None:
        self.current_reconstruction: Optional[Reconstruction] = None
        self.original_audio: Optional[np.ndarray] = None
        self.reconstructor_generators: List[GeneratorName] = GENERATOR_NAMES.copy()
        self.selected_generators = {generator_name: True for generator_name in GENERATOR_NAMES}
        self.audio_path: Optional[Path] = None
        self.reconstruction_path: Optional[Path] = None
        self.config_manager = ConfigManager()
        self.config_panel = ConfigPanelGUI(self.config_manager)
        self.library_panel = LibraryPanelGUI(
            self.config_manager, on_config_gui_update=self.config_panel.apply_library_config
        )

        self.setup_gui()

    def setup_gui(self) -> None:
        dpg.create_context()

        self.create_main_window()
        dpg.create_viewport(title=WINDOW_TITLE, width=MAIN_WINDOW_WIDTH, height=MAIN_WINDOW_HEIGHT)
        dpg.setup_dearpygui()

        dpg.show_viewport()

    def create_main_window(self) -> None:
        with dpg.window(label=WINDOW_TITLE, tag=TAG_MAIN_WINDOW):
            with dpg.menu_bar():
                with dpg.menu(label=MENU_FILE):
                    dpg.add_menu_item(label=MENU_LOAD_CONFIG, callback=self.load_config_dialog)
                    dpg.add_menu_item(label=MENU_LOAD_AUDIO, callback=self.load_audio_dialog)
                    dpg.add_menu_item(label=MENU_LOAD_RECONSTRUCTION, callback=self.load_reconstruction_dialog)
                    dpg.add_separator()
                    dpg.add_menu_item(label=MENU_EXIT, callback=lambda: dpg.stop_dearpygui())

            with dpg.tab_bar():
                self.create_config_tab()
                self.create_reconstruction_tab()
                self.create_browser_tab()

        dpg.set_primary_window(TAG_MAIN_WINDOW, PRIMARY_WINDOW_ENABLED)

    def create_config_tab(self) -> None:
        with dpg.tab(label=TAB_CONFIGURATION):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=LIBRARY_PANEL_WIDTH, height=-1):
                    with dpg.group(tag=TAG_CONFIG_PANEL_GROUP):
                        self.config_panel.create_panel(TAG_CONFIG_PANEL_GROUP)

                    with dpg.group(tag=TAG_LIBRARY_PANEL_GROUP):
                        self.library_panel.create_panel()

                self.config_panel.create_preview_panel(TAG_CONFIG_TAB)

        self.config_manager.add_config_change_callback(self.library_panel.update_status)
        self.config_manager.initialize_config_with_defaults()
        self.library_panel.initialize_libraries()

    def create_reconstruction_tab(self) -> None:
        with dpg.tab(label=TAB_RECONSTRUCTION):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=RECONSTRUCTION_PANEL_WIDTH, height=RECONSTRUCTION_PANEL_HEIGHT):
                    dpg.add_text(SECTION_AUDIO_INPUT)
                    dpg.add_separator()

                    dpg.add_button(label=BUTTON_SELECT_AUDIO_FILE, callback=self.load_audio_dialog)
                    dpg.add_text(MSG_NO_FILE_SELECTED, tag=TAG_SELECTED_AUDIO_FILE)

                    dpg.add_separator()
                    dpg.add_button(label=BUTTON_START_RECONSTRUCTION, callback=self.start_reconstruction)
                    dpg.add_progress_bar(tag=TAG_RECONSTRUCTION_PROGRESS, default_value=DEFAULT_FLOAT_VALUE)

                    dpg.add_separator()
                    dpg.add_text(SECTION_GENERATOR_SELECTION)
                    dpg.add_checkbox(
                        label=CHECKBOX_TRIANGLE, default_value=CHECKBOX_DEFAULT_ENABLED, tag=TAG_GEN_TRIANGLE
                    )
                    dpg.add_checkbox(label=CHECKBOX_PULSE_1, default_value=CHECKBOX_DEFAULT_ENABLED, tag=TAG_GEN_PULSE1)
                    dpg.add_checkbox(label=CHECKBOX_PULSE_2, default_value=CHECKBOX_DEFAULT_ENABLED, tag=TAG_GEN_PULSE2)
                    dpg.add_checkbox(label=CHECKBOX_NOISE, default_value=CHECKBOX_DEFAULT_ENABLED, tag=TAG_GEN_NOISE)

                    dpg.add_separator()
                    dpg.add_button(label=BUTTON_PLAY_ORIGINAL, callback=self.play_original)
                    dpg.add_button(label=BUTTON_PLAY_RECONSTRUCTION, callback=self.play_reconstruction)
                    dpg.add_button(label=BUTTON_EXPORT_WAV, callback=self.export_wav_dialog)

                with dpg.child_window():
                    dpg.add_text(SECTION_WAVEFORM_DISPLAY)
                    dpg.add_separator()

                    with dpg.plot(
                        label=PLOT_AUDIO_WAVEFORMS,
                        height=WAVEFORM_PLOT_HEIGHT,
                        width=PLOT_WIDTH_FULL,
                        tag=TAG_WAVEFORM_PLOT,
                    ):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(dpg.mvXAxis, label=PLOT_TIME_SAMPLES, tag=TAG_X_AXIS)
                        dpg.add_plot_axis(dpg.mvYAxis, label=PLOT_AMPLITUDE, tag=TAG_Y_AXIS)

                    dpg.add_separator()
                    dpg.add_text(MSG_RECONSTRUCTION_INFO, tag=TAG_RECONSTRUCTION_INFO)

    def create_browser_tab(self) -> None:
        with dpg.tab(label=TAB_BROWSER):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=BROWSER_PANEL_WIDTH, height=BROWSER_PANEL_HEIGHT):
                    dpg.add_text(SECTION_SAVED_RECONSTRUCTIONS)
                    dpg.add_separator()

                    dpg.add_button(label=BUTTON_REFRESH_LIST, callback=self.refresh_reconstruction_list)
                    dpg.add_listbox([], tag=TAG_RECONSTRUCTION_LIST, callback=self.load_selected_reconstruction)

                with dpg.child_window():
                    dpg.add_text(SECTION_RECONSTRUCTION_DETAILS)
                    dpg.add_separator()

                    dpg.add_text(MSG_SELECT_RECONSTRUCTION, tag=TAG_RECONSTRUCTION_DETAILS)

                    dpg.add_separator()
                    dpg.add_text(SECTION_FAMITRACKER_EXPORT)
                    dpg.add_input_text(
                        label=LABEL_EMPTY,
                        tag=TAG_FAMITRACKER_EXPORT,
                        multiline=True,
                        height=FAMITRACKER_EXPORT_HEIGHT,
                        readonly=True,
                    )

    def load_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=DIALOG_LOAD_CONFIG,
            width=FILE_DIALOG_WIDTH,
            height=FILE_DIALOG_HEIGHT,
            callback=self.load_config,
            file_count=FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_JSON)

    def load_audio_dialog(self) -> None:
        with dpg.file_dialog(
            label=DIALOG_LOAD_AUDIO,
            width=FILE_DIALOG_WIDTH,
            height=FILE_DIALOG_HEIGHT,
            callback=self.load_audio,
            file_count=FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_WAV)

    def load_reconstruction_dialog(self) -> None:
        with dpg.file_dialog(
            label=DIALOG_LOAD_RECONSTRUCTION,
            width=FILE_DIALOG_WIDTH,
            height=FILE_DIALOG_HEIGHT,
            callback=self.load_reconstruction,
            file_count=FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_JSON)

    def select_library_directory_dialog(self) -> None:
        with dpg.file_dialog(
            label=DIALOG_SELECT_LIBRARY_DIR,
            width=FILE_DIALOG_WIDTH,
            height=FILE_DIALOG_HEIGHT,
            callback=self.select_library_directory,
            directory_selector=True,
        ):
            pass

    def export_wav_dialog(self) -> None:
        if not self.current_reconstruction:
            return

        with dpg.file_dialog(
            label=DIALOG_EXPORT_WAV,
            width=FILE_DIALOG_WIDTH,
            height=FILE_DIALOG_HEIGHT,
            callback=self.export_wav,
            file_count=FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_WAV)

    def load_config(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data[KEY_SELECTIONS].values())[INDEX_FIRST_SELECTION]
        with open(file_path, "r") as f:
            config_data = json.load(f)
        if self.config_panel.load_config_from_data(config_data):
            dpg.set_value(TAG_CONFIG_PREVIEW, LOADED_PREFIX.format(Path(file_path).name))

    def load_audio(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data[KEY_SELECTIONS].values())[INDEX_FIRST_SELECTION]
        self.audio_path = Path(file_path)
        self.original_audio = load_audio(self.audio_path)
        dpg.set_value(TAG_SELECTED_AUDIO_FILE, self.audio_path.name)

    def load_reconstruction(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data[KEY_SELECTIONS].values())[INDEX_FIRST_SELECTION]
        self.current_reconstruction = Reconstruction.load(file_path)
        dpg.set_value(TAG_RECONSTRUCTION_DETAILS, LOADED_PREFIX.format(Path(file_path).name))

    def select_library_directory(self, sender: Any, app_data: Dict[str, Any]) -> None:
        directory_path = list(app_data[KEY_SELECTIONS].values())[INDEX_FIRST_SELECTION]
        self.config_manager.set_library_directory(directory_path)
        gui_values = {}
        for tag in self.config_manager.config_params.keys():
            gui_values[tag] = dpg.get_value(tag)
        self.config_manager.update_config_from_gui_values(gui_values)
        dpg.set_value(TAG_LIBRARY_DIRECTORY_DISPLAY, CUSTOM_LIBRARY_DIR_DISPLAY.format(Path(directory_path).name))

    def start_reconstruction(self) -> None:
        if self.original_audio is None or not self.audio_path:
            dpg.set_value(TAG_RECONSTRUCTION_INFO, MSG_SELECT_AUDIO_FIRST)
            return

        config = self.config_manager.get_config()
        if not config:
            dpg.set_value(TAG_RECONSTRUCTION_INFO, MSG_CONFIG_ERROR)
            return

        generator_names: List[GeneratorName] = [
            name for name in GENERATOR_NAMES if dpg.get_value(TEMPLATE_RECONSTRUCTION_GEN_TAG.format(name))
        ]
        reconstructor = Reconstructor(config, generator_names)
        self.current_reconstruction = reconstructor(self.audio_path)

        self.update_waveform_display()

        dpg.set_value(TAG_RECONSTRUCTION_PROGRESS, PROGRESS_COMPLETE_VALUE)
        dpg.set_value(
            TAG_RECONSTRUCTION_INFO,
            MSG_RECONSTRUCTION_COMPLETE.format(self.current_reconstruction.total_error),
        )

    def update_waveform_display(self) -> None:
        if not self.current_reconstruction:
            return

        dpg.delete_item(TAG_WAVEFORM_PLOT, children_only=True, slot=PLOT_CHILDREN_SLOT)
        with dpg.plot(
            label=PLOT_AUDIO_WAVEFORMS, height=WAVEFORM_PLOT_HEIGHT, width=PLOT_WIDTH_FULL, parent=TAG_WAVEFORM_PLOT
        ):
            dpg.add_plot_legend()
            x_axis = dpg.add_plot_axis(dpg.mvXAxis, label=PLOT_TIME_SAMPLES)
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=PLOT_AMPLITUDE)

            x_data = [float(i) for i in range(len(self.current_reconstruction.approximation))]
            if self.original_audio is not None:
                dpg.add_line_series(
                    x_data[: len(self.original_audio)], self.original_audio.tolist(), label=PLOT_ORIGINAL, parent=y_axis
                )

            dpg.add_line_series(
                x_data, self.current_reconstruction.approximation.tolist(), label=PLOT_RECONSTRUCTION, parent=y_axis
            )

    def play_original(self) -> None:
        if self.original_audio is not None:
            play_audio(self.original_audio)

    def play_reconstruction(self) -> None:
        if self.current_reconstruction:
            play_audio(self.current_reconstruction.approximation)

    def export_wav(self, sender: Any, app_data: Dict[str, Any]) -> None:
        if not self.current_reconstruction:
            return

        file_path = list(app_data[KEY_SELECTIONS].values())[INDEX_FIRST_SELECTION]
        write_audio(Path(file_path), self.current_reconstruction.approximation)

    def refresh_reconstruction_list(self) -> None:
        pass

    def load_selected_reconstruction(self) -> None:
        pass

    def run(self) -> None:
        dpg.start_dearpygui()
        dpg.destroy_context()
