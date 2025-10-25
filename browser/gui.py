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
        self.library_panel = LibraryPanelGUI(self.config_manager)

        self.setup_gui()

    def setup_gui(self) -> None:
        dpg.create_context()

        self.create_main_window()
        dpg.create_viewport(title=WINDOW_TITLE, width=MAIN_WINDOW_WIDTH, height=MAIN_WINDOW_HEIGHT)
        dpg.setup_dearpygui()

        dpg.show_viewport()

    def create_main_window(self) -> None:
        with dpg.window(label=WINDOW_TITLE, tag="main_window"):
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

        dpg.set_primary_window("main_window", True)

    def create_config_tab(self) -> None:
        with dpg.tab(label=TAB_CONFIGURATION):
            with dpg.group(horizontal=True):
                with dpg.group(tag="left_panels_group"):
                    with dpg.group(tag="config_panel_group"):
                        self.config_panel.create_panel("config_panel_group")

                    with dpg.group(tag="library_panel_group"):
                        self.library_panel.create_panel("library_panel_group")

                self.config_panel.create_preview_panel("config_tab")

        self.config_manager.add_config_change_callback(self.library_panel.update_status)
        self.config_manager.initialize_config_with_defaults()

    def create_reconstruction_tab(self) -> None:
        with dpg.tab(label=TAB_RECONSTRUCTION):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=RECONSTRUCTION_PANEL_WIDTH, height=RECONSTRUCTION_PANEL_HEIGHT):
                    dpg.add_text(SECTION_AUDIO_INPUT)
                    dpg.add_separator()

                    dpg.add_button(label=BUTTON_SELECT_AUDIO_FILE, callback=self.load_audio_dialog)
                    dpg.add_text(MSG_NO_FILE_SELECTED, tag="selected_audio_file")

                    dpg.add_separator()
                    dpg.add_button(label=BUTTON_START_RECONSTRUCTION, callback=self.start_reconstruction)
                    dpg.add_progress_bar(tag="reconstruction_progress", default_value=0.0)

                    dpg.add_separator()
                    dpg.add_text(SECTION_GENERATOR_SELECTION)
                    dpg.add_checkbox(label=CHECKBOX_TRIANGLE, default_value=True, tag="gen_triangle")
                    dpg.add_checkbox(label=CHECKBOX_PULSE_1, default_value=True, tag="gen_pulse1")
                    dpg.add_checkbox(label=CHECKBOX_PULSE_2, default_value=True, tag="gen_pulse2")
                    dpg.add_checkbox(label=CHECKBOX_NOISE, default_value=True, tag="gen_noise")

                    dpg.add_separator()
                    dpg.add_button(label=BUTTON_PLAY_ORIGINAL, callback=self.play_original)
                    dpg.add_button(label=BUTTON_PLAY_RECONSTRUCTION, callback=self.play_reconstruction)
                    dpg.add_button(label=BUTTON_EXPORT_WAV, callback=self.export_wav_dialog)

                with dpg.child_window():
                    dpg.add_text(SECTION_WAVEFORM_DISPLAY)
                    dpg.add_separator()

                    with dpg.plot(
                        label=PLOT_AUDIO_WAVEFORMS, height=WAVEFORM_PLOT_HEIGHT, width=-1, tag="waveform_plot"
                    ):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(dpg.mvXAxis, label=PLOT_TIME_SAMPLES, tag="x_axis")
                        dpg.add_plot_axis(dpg.mvYAxis, label=PLOT_AMPLITUDE, tag="y_axis")

                    dpg.add_separator()
                    dpg.add_text("Reconstruction info", tag="reconstruction_info")

    def create_browser_tab(self) -> None:
        with dpg.tab(label=TAB_BROWSER):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=BROWSER_PANEL_WIDTH, height=BROWSER_PANEL_HEIGHT):
                    dpg.add_text(SECTION_SAVED_RECONSTRUCTIONS)
                    dpg.add_separator()

                    dpg.add_button(label=BUTTON_REFRESH_LIST, callback=self.refresh_reconstruction_list)
                    dpg.add_listbox([], tag="reconstruction_list", callback=self.load_selected_reconstruction)

                with dpg.child_window():
                    dpg.add_text(SECTION_RECONSTRUCTION_DETAILS)
                    dpg.add_separator()

                    dpg.add_text(MSG_SELECT_RECONSTRUCTION, tag="reconstruction_details")

                    dpg.add_separator()
                    dpg.add_text(SECTION_FAMITRACKER_EXPORT)
                    dpg.add_input_text(
                        label="",
                        tag="famitracker_export",
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
            file_count=1,
        ):
            dpg.add_file_extension(EXT_JSON)

    def load_audio_dialog(self) -> None:
        with dpg.file_dialog(
            label=DIALOG_LOAD_AUDIO,
            width=FILE_DIALOG_WIDTH,
            height=FILE_DIALOG_HEIGHT,
            callback=self.load_audio,
            file_count=1,
        ):
            dpg.add_file_extension(EXT_WAV)

    def load_reconstruction_dialog(self) -> None:
        with dpg.file_dialog(
            label=DIALOG_LOAD_RECONSTRUCTION,
            width=FILE_DIALOG_WIDTH,
            height=FILE_DIALOG_HEIGHT,
            callback=self.load_reconstruction,
            file_count=1,
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
            file_count=1,
        ):
            dpg.add_file_extension(EXT_WAV)

    def load_config(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data["selections"].values())[0]
        try:
            with open(file_path, "r") as f:
                config_data = json.load(f)
            if self.config_panel.load_config_from_data(config_data):
                dpg.set_value("config_preview", LOADED_PREFIX.format(Path(file_path).name))
        except Exception as exception:  # TODO: to narrow
            dpg.set_value("config_preview", ERROR_PREFIX.format(f"loading config: {exception}"))

    def load_audio(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data["selections"].values())[0]
        try:
            self.audio_path = Path(file_path)
            self.original_audio = load_audio(self.audio_path)
            dpg.set_value("selected_audio_file", self.audio_path.name)
        except Exception as exception:  # TODO: to narrow
            dpg.set_value("selected_audio_file", ERROR_PREFIX.format(str(exception)))

    def load_reconstruction(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data["selections"].values())[0]
        try:
            self.current_reconstruction = Reconstruction.load(file_path)
            dpg.set_value("reconstruction_details", LOADED_PREFIX.format(Path(file_path).name))
        except Exception as exception:  # TODO: to narrow
            dpg.set_value("reconstruction_details", ERROR_PREFIX.format(f"loading reconstruction: {exception}"))

    def select_library_directory(self, sender: Any, app_data: Dict[str, Any]) -> None:
        directory_path = list(app_data["selections"].values())[0]
        try:
            self.config_manager.set_library_directory(directory_path)
            gui_values = {}
            for tag in self.config_manager.config_params.keys():
                gui_values[tag] = dpg.get_value(tag)
            self.config_manager.update_config_from_gui_values(gui_values)
            dpg.set_value("library_directory_display", CUSTOM_LIBRARY_DIR_DISPLAY.format(Path(directory_path).name))
        except Exception as exception:  # TODO: to narrow
            dpg.set_value("library_directory_display", ERROR_PREFIX.format(str(exception)))

    def start_reconstruction(self) -> None:
        if self.original_audio is None or not self.audio_path:
            dpg.set_value("reconstruction_info", "Please select an audio file first")
            return

        config = self.config_manager.get_config()
        if not config:
            dpg.set_value("reconstruction_info", "Configuration error - please check settings")
            return

        try:
            generator_names: List[GeneratorName] = [name for name in GENERATOR_NAMES if dpg.get_value(f"gen_{name}")]
            reconstructor = Reconstructor(config, generator_names)
            self.current_reconstruction = reconstructor(self.audio_path)

            self.update_waveform_display()

            dpg.set_value("reconstruction_progress", 1.0)
            dpg.set_value(
                "reconstruction_info",
                MSG_RECONSTRUCTION_COMPLETE.format(self.current_reconstruction.total_error),
            )

        except Exception as exception:  # TODO: to narrow
            dpg.set_value("reconstruction_info", ERROR_PREFIX.format(f"during reconstruction: {exception}"))

    def update_waveform_display(self) -> None:
        if not self.current_reconstruction:
            return

        dpg.delete_item("waveform_plot", children_only=True, slot=2)
        with dpg.plot(label=PLOT_AUDIO_WAVEFORMS, height=WAVEFORM_PLOT_HEIGHT, width=-1, parent="waveform_plot"):
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

        file_path = list(app_data["selections"].values())[0]
        try:
            write_audio(Path(file_path), self.current_reconstruction.approximation)
        except Exception as exception:  # TODO: to narrow
            print(ERROR_PREFIX.format(f"exporting WAV: {exception}"))

    def refresh_reconstruction_list(self) -> None:
        pass
        # TODO: implement
        # dpg.configure_item("reconstruction_list", items=reconstructions)

    def load_selected_reconstruction(self) -> None:
        pass
        # TODO: implement
        # selected = dpg.get_value("reconstruction_list")
        # if selected:
        #     dpg.set_value("reconstruction_details", f"Loaded: {selected}")

    def run(self) -> None:
        dpg.start_dearpygui()
        dpg.destroy_context()
