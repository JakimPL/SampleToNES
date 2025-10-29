import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import dearpygui.dearpygui as dpg
import numpy as np

from browser.config.manager import ConfigManager
from browser.config.panel import ConfigPanelGUI
from browser.constants import *
from browser.instruction.panel import GUIInstructionPanel
from browser.library.panel import GUILibraryPanel
from configs.library import LibraryConfig
from library.data import LibraryFragment
from reconstructor.reconstruction import Reconstruction
from reconstructor.reconstructor import Reconstructor
from typehints.general import GENERATOR_NAMES, GeneratorName
from utils.audio.device import AudioDeviceManager
from utils.audio.io import load_audio, write_audio


class GUI:
    def __init__(self) -> None:
        self.current_reconstruction: Optional[Reconstruction] = None
        self.original_audio: Optional[np.ndarray] = None
        self.reconstructor_generators: List[GeneratorName] = GENERATOR_NAMES.copy()
        self.selected_generators = {generator_name: True for generator_name in GENERATOR_NAMES}
        self.audio_path: Optional[Path] = None
        self.reconstruction_path: Optional[Path] = None
        self.audio_device_manager = AudioDeviceManager()
        self.config_manager = ConfigManager()
        self.config_panel = ConfigPanelGUI(self.config_manager)
        self.instruction_panel: Optional[GUIInstructionPanel] = None
        self.library_panel = GUILibraryPanel(
            self.config_manager,
            on_instruction_selected=self._on_instruction_selected,
            on_config_gui_update=self.config_panel.apply_library_config,
        )

        self.setup_gui()

    def setup_gui(self) -> None:
        dpg.create_context()
        self.create_main_window()
        dpg.create_viewport(title=TITLE_WINDOW_MAIN, width=DIM_WINDOW_MAIN_WIDTH, height=DIM_WINDOW_MAIN_HEIGHT)
        dpg.setup_dearpygui()
        dpg.show_viewport()

    def create_main_window(self) -> None:
        with dpg.window(label=TITLE_WINDOW_MAIN, tag=TAG_WINDOW_MAIN):
            with dpg.menu_bar():
                with dpg.menu(label=LBL_MENU_FILE):
                    dpg.add_menu_item(label=LBL_MENU_LOAD_CONFIG, callback=self.load_config_dialog)
                    dpg.add_menu_item(label=LBL_MENU_LOAD_AUDIO, callback=self.load_audio_dialog)
                    dpg.add_menu_item(label=LBL_MENU_LOAD_RECONSTRUCTION, callback=self.load_reconstruction_dialog)
                    dpg.add_separator()
                    dpg.add_menu_item(label=LBL_MENU_EXIT, callback=lambda: dpg.stop_dearpygui())

            with dpg.tab_bar():
                self.create_config_tab()
                self.create_reconstruction_tab()
                self.create_browser_tab()

        dpg.set_primary_window(TAG_WINDOW_MAIN, FLAG_WINDOW_PRIMARY_ENABLED)

    def create_config_tab(self) -> None:
        with dpg.tab(label=LBL_TAB_LIBRARY):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=DIM_PANEL_LEFT_WIDTH, height=-1):
                    with dpg.group(tag=TAG_CONFIG_PANEL_GROUP):
                        self.config_panel.create_panel()

                    with dpg.group(tag=TAG_LIBRARY_PANEL_GROUP):
                        self.library_panel.create_panel()

                with dpg.child_window(tag=TAG_INSTRUCTION_PANEL_GROUP):
                    self.instruction_panel = GUIInstructionPanel(self.audio_device_manager)
                    self.instruction_panel.create_panel()

        self.config_manager.add_config_change_callback(self.library_panel.update_status)
        self.config_manager.initialize_config_with_defaults()
        self.library_panel.initialize_libraries()

    def create_reconstruction_tab(self) -> None:
        with dpg.tab(label=LBL_TAB_RECONSTRUCTION):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=DIM_PANEL_RECONSTRUCTION_WIDTH, height=DIM_PANEL_RECONSTRUCTION_HEIGHT):
                    dpg.add_text(LBL_SECTION_AUDIO_INPUT)
                    dpg.add_separator()

                    dpg.add_button(label=LBL_BUTTON_SELECT_AUDIO_FILE, callback=self.load_audio_dialog)
                    dpg.add_text(MSG_GLOBAL_NO_FILE_SELECTED, tag=TAG_RECONSTRUCTION_SELECTED_AUDIO_FILE)

                    dpg.add_separator()
                    dpg.add_button(label=LBL_BUTTON_START_RECONSTRUCTION, callback=self.start_reconstruction)
                    dpg.add_progress_bar(tag=TAG_RECONSTRUCTION_PROGRESS, default_value=VAL_GLOBAL_DEFAULT_FLOAT)

                    dpg.add_separator()
                    dpg.add_text(LBL_SECTION_GENERATOR_SELECTION)
                    dpg.add_checkbox(
                        label=LBL_CHECKBOX_TRIANGLE,
                        default_value=FLAG_CHECKBOX_DEFAULT_ENABLED,
                        tag=TPL_RECONSTRUCTION_GEN_TAG.format("triangle"),
                    )
                    dpg.add_checkbox(
                        label=LBL_CHECKBOX_PULSE_1,
                        default_value=FLAG_CHECKBOX_DEFAULT_ENABLED,
                        tag=TPL_RECONSTRUCTION_GEN_TAG.format("pulse1"),
                    )
                    dpg.add_checkbox(
                        label=LBL_CHECKBOX_PULSE_2,
                        default_value=FLAG_CHECKBOX_DEFAULT_ENABLED,
                        tag=TPL_RECONSTRUCTION_GEN_TAG.format("pulse2"),
                    )
                    dpg.add_checkbox(
                        label=LBL_CHECKBOX_NOISE,
                        default_value=FLAG_CHECKBOX_DEFAULT_ENABLED,
                        tag=TPL_RECONSTRUCTION_GEN_TAG.format("noise"),
                    )

                    dpg.add_separator()
                    # dpg.add_button(label=LBL_BUTTON_PLAY_ORIGINAL, callback=self.play_original)
                    # dpg.add_button(label=LBL_BUTTON_PLAY_RECONSTRUCTION, callback=self.play_reconstruction)
                    # dpg.add_button(label=LBL_BUTTON_EXPORT_WAV, callback=self.export_wav_dialog)

                with dpg.child_window():
                    dpg.add_text(LBL_SECTION_WAVEFORM_DISPLAY)
                    dpg.add_separator()

                    with dpg.plot(
                        label=LBL_PLOT_AUDIO_WAVEFORMS,
                        height=DIM_WAVEFORM_PLOT_HEIGHT,
                        width=VAL_PLOT_WIDTH_FULL,
                        tag=TAG_WAVEFORM_PLOT,
                    ):
                        dpg.add_plot_legend()
                        dpg.add_plot_axis(dpg.mvXAxis, label=LBL_PLOT_TIME_SAMPLES, tag=TAG_PLOT_X_AXIS)
                        dpg.add_plot_axis(dpg.mvYAxis, label=LBL_PLOT_AMPLITUDE, tag=TAG_PLOT_Y_AXIS)

                    dpg.add_separator()
                    dpg.add_text(MSG_RECONSTRUCTION_INFO, tag=TAG_RECONSTRUCTION_INFO)

    def create_browser_tab(self) -> None:
        with dpg.tab(label=LBL_TAB_BROWSER):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=DIM_PANEL_BROWSER_WIDTH, height=DIM_PANEL_BROWSER_HEIGHT):
                    dpg.add_text(LBL_SECTION_SAVED_RECONSTRUCTIONS)
                    dpg.add_separator()

                    dpg.add_button(label=LBL_BUTTON_REFRESH_LIST, callback=self.refresh_reconstruction_list)
                    dpg.add_listbox([], tag=TAG_BROWSER_RECONSTRUCTION_LIST, callback=self.load_selected_reconstruction)

                with dpg.child_window():
                    dpg.add_text(LBL_SECTION_RECONSTRUCTION_DETAILS)
                    dpg.add_separator()

                    dpg.add_text(MSG_RECONSTRUCTION_SELECT_TO_VIEW, tag=TAG_BROWSER_RECONSTRUCTION_DETAILS)

                    dpg.add_separator()
                    dpg.add_text(LBL_SECTION_FAMITRACKER_EXPORT)
                    dpg.add_input_text(
                        label=LBL_GLOBAL_EMPTY,
                        tag=TAG_BROWSER_FAMITRACKER_EXPORT,
                        multiline=True,
                        height=DIM_FAMITRACKER_EXPORT_HEIGHT,
                        readonly=True,
                    )

    def load_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_LOAD_CONFIG,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self.load_config,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_DIALOG_JSON)

    def load_audio_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_LOAD_AUDIO,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self.load_audio,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_DIALOG_WAV)

    def load_reconstruction_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_LOAD_RECONSTRUCTION,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self.load_reconstruction,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_DIALOG_JSON)

    def select_library_directory_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_SELECT_LIBRARY_DIR,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self.select_library_directory,
            directory_selector=True,
        ):
            pass

    def export_wav_dialog(self) -> None:
        if not self.current_reconstruction:
            return

        with dpg.file_dialog(
            label=TITLE_DIALOG_EXPORT_WAV,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self.export_wav,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_DIALOG_WAV)

    def load_config(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data[KEY_DIALOG_SELECTIONS].values())[IDX_DIALOG_FIRST_SELECTION]
        with open(file_path, "r") as f:
            config_data = json.load(f)
        self.config_panel.load_config_from_data(config_data)

    def load_audio(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data[KEY_DIALOG_SELECTIONS].values())[IDX_DIALOG_FIRST_SELECTION]
        self.audio_path = Path(file_path)
        self.original_audio = load_audio(self.audio_path)
        dpg.set_value(TAG_RECONSTRUCTION_SELECTED_AUDIO_FILE, self.audio_path.name)

    def load_reconstruction(self, sender: Any, app_data: Dict[str, Any]) -> None:
        file_path = list(app_data[KEY_DIALOG_SELECTIONS].values())[IDX_DIALOG_FIRST_SELECTION]
        self.current_reconstruction = Reconstruction.load(file_path)
        dpg.set_value(TAG_BROWSER_RECONSTRUCTION_DETAILS, PFX_GLOBAL_LOADED.format(Path(file_path).name))

    def select_library_directory(self, sender: Any, app_data: Dict[str, Any]) -> None:
        directory_path = list(app_data[KEY_DIALOG_SELECTIONS].values())[IDX_DIALOG_FIRST_SELECTION]
        self.config_manager.set_library_directory(directory_path)
        gui_values = {}
        for tag in self.config_manager.config_params.keys():
            gui_values[tag] = dpg.get_value(tag)
        self.config_manager.update_config_from_gui_values(gui_values)
        dpg.set_value(TAG_LIBRARY_DIRECTORY_DISPLAY, TPL_LIBRARY_CUSTOM_DIR_DISPLAY.format(Path(directory_path).name))

    def start_reconstruction(self) -> None:
        if self.original_audio is None or not self.audio_path:
            dpg.set_value(TAG_RECONSTRUCTION_INFO, MSG_RECONSTRUCTION_SELECT_AUDIO_FIRST)
            return

        config = self.config_manager.get_config()
        if not config:
            dpg.set_value(TAG_RECONSTRUCTION_INFO, MSG_CONFIG_ERROR)
            return

        generator_names: List[GeneratorName] = [
            name for name in GENERATOR_NAMES if dpg.get_value(TPL_RECONSTRUCTION_GEN_TAG.format(name))
        ]
        reconstructor = Reconstructor(config, generator_names)
        self.current_reconstruction = reconstructor(self.audio_path)

        self.update_waveform_display()

        dpg.set_value(TAG_RECONSTRUCTION_PROGRESS, VAL_GLOBAL_PROGRESS_COMPLETE)
        dpg.set_value(
            TAG_RECONSTRUCTION_INFO,
            TPL_RECONSTRUCTION_COMPLETE.format(self.current_reconstruction.total_error),
        )

    def update_waveform_display(self) -> None:
        if not self.current_reconstruction:
            return

        dpg.delete_item(TAG_WAVEFORM_PLOT, children_only=True, slot=VAL_PLOT_CHILDREN_SLOT)
        with dpg.plot(
            label=LBL_PLOT_AUDIO_WAVEFORMS,
            height=DIM_WAVEFORM_PLOT_HEIGHT,
            width=VAL_PLOT_WIDTH_FULL,
            parent=TAG_WAVEFORM_PLOT,
        ):
            dpg.add_plot_legend()
            x_axis = dpg.add_plot_axis(dpg.mvXAxis, label=LBL_PLOT_TIME_SAMPLES)
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=LBL_PLOT_AMPLITUDE)

            x_data = [float(i) for i in range(len(self.current_reconstruction.approximation))]
            if self.original_audio is not None:
                dpg.add_line_series(
                    x_data[: len(self.original_audio)],
                    self.original_audio.tolist(),
                    label=LBL_PLOT_ORIGINAL,
                    parent=y_axis,
                )

            dpg.add_line_series(
                x_data, self.current_reconstruction.approximation.tolist(), label=LBL_PLOT_RECONSTRUCTION, parent=y_axis
            )

    def export_wav(self, sender: Any, app_data: Dict[str, Any]) -> None:
        if not self.current_reconstruction:
            return

        file_path = list(app_data[KEY_DIALOG_SELECTIONS].values())[IDX_DIALOG_FIRST_SELECTION]
        sample_rate = self.current_reconstruction.config.library.sample_rate
        write_audio(Path(file_path), self.current_reconstruction.approximation, sample_rate)

    def refresh_reconstruction_list(self) -> None:
        pass

    def load_selected_reconstruction(self) -> None:
        pass

    def _on_instruction_selected(
        self, generator_class_name: str, instruction, fragment: LibraryFragment, library_config: LibraryConfig
    ) -> None:
        if self.instruction_panel:
            self.instruction_panel.display_instruction(generator_class_name, instruction, fragment, library_config)

    def run(self) -> None:
        dpg.start_dearpygui()
        dpg.destroy_context()
