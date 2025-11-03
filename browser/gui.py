import dearpygui.dearpygui as dpg

from browser.browser.panel import GUIBrowserPanel
from browser.config.manager import ConfigManager
from browser.config.panel import GUIConfigPanel
from browser.instruction.panel import GUIInstructionPanel
from browser.library.panel import GUILibraryPanel
from browser.reconstruction.data import ReconstructionData
from browser.reconstruction.panel import GUIReconstructionPanel
from browser.reconstructor.panel import GUIReconstructorPanel
from configs.library import LibraryConfig
from constants.browser import (
    DIM_DIALOG_FILE_HEIGHT,
    DIM_DIALOG_FILE_WIDTH,
    DIM_PANEL_LEFT_WIDTH,
    DIM_WINDOW_MAIN_HEIGHT,
    DIM_WINDOW_MAIN_WIDTH,
    EXT_DIALOG_JSON,
    EXT_DIALOG_WAV,
    FLAG_WINDOW_PRIMARY_ENABLED,
    LBL_MENU_EXIT,
    LBL_MENU_FILE,
    LBL_MENU_LOAD_AUDIO,
    LBL_MENU_LOAD_CONFIG,
    LBL_MENU_LOAD_RECONSTRUCTION,
    LBL_TAB_LIBRARY,
    LBL_TAB_RECONSTRUCTION,
    TAG_BROWSER_PANEL_GROUP,
    TAG_CONFIG_PANEL_GROUP,
    TAG_INSTRUCTION_PANEL_GROUP,
    TAG_LIBRARY_PANEL_GROUP,
    TAG_RECONSTRUCTION_PANEL_GROUP,
    TAG_RECONSTRUCTOR_PANEL_GROUP,
    TAG_WINDOW_MAIN,
    TITLE_DIALOG_EXPORT_WAV,
    TITLE_DIALOG_LOAD_AUDIO,
    TITLE_DIALOG_LOAD_CONFIG,
    TITLE_DIALOG_LOAD_RECONSTRUCTION,
    TITLE_WINDOW_MAIN,
    VAL_DIALOG_FILE_COUNT_SINGLE,
)
from library.data import LibraryFragment
from utils.audio.device import AudioDeviceManager


class GUI:
    def __init__(self) -> None:
        self.audio_device_manager = AudioDeviceManager()
        self.config_manager = ConfigManager()

        self.config_panel: GUIConfigPanel = GUIConfigPanel(self.config_manager)
        self.library_panel: GUILibraryPanel = GUILibraryPanel(self.config_manager)
        self.instruction_panel: GUIInstructionPanel = GUIInstructionPanel(self.audio_device_manager)

        self.reconstructor_panel: GUIReconstructorPanel = GUIReconstructorPanel(self.config_manager)
        self.browser_panel: GUIBrowserPanel = GUIBrowserPanel(self.config_manager)
        self.reconstruction_panel: GUIReconstructionPanel = GUIReconstructionPanel(
            self.config_manager, self.audio_device_manager
        )

        self.setup_gui()

    def setup_gui(self) -> None:
        dpg.create_context()
        self.create_main_window()
        dpg.create_viewport(title=TITLE_WINDOW_MAIN, width=DIM_WINDOW_MAIN_WIDTH, height=DIM_WINDOW_MAIN_HEIGHT)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        self.set_callbacks()

    def set_callbacks(self) -> None:
        self.config_manager.add_config_change_callback(self.library_panel.update_status)
        self.library_panel.set_callbacks(
            on_instruction_selected=self._on_instruction_selected,
            on_apply_library_config=self.config_panel.apply_library_config,
        )
        self.browser_panel.set_callbacks(
            on_reconstruction_selected=self._on_reconstruction_selected,
        )

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
                    self.instruction_panel.create_panel()

        self.config_manager.initialize_config_with_defaults()
        self.library_panel.initialize_libraries()

    def create_reconstruction_tab(self) -> None:
        with dpg.tab(label=LBL_TAB_RECONSTRUCTION):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=DIM_PANEL_LEFT_WIDTH, height=-1):
                    with dpg.group(tag=TAG_RECONSTRUCTOR_PANEL_GROUP):
                        self.reconstructor_panel.create_panel()

                    with dpg.group(tag=TAG_BROWSER_PANEL_GROUP):
                        self.browser_panel.create_panel()

                with dpg.child_window(tag=TAG_RECONSTRUCTION_PANEL_GROUP):
                    self.reconstruction_panel.create_panel()

        self.browser_panel.initialize_tree()

    def load_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_LOAD_CONFIG,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            # callback=self.load_config,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_DIALOG_JSON)

    def load_audio_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_LOAD_AUDIO,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            # callback=self.load_audio,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_DIALOG_WAV)

    def load_reconstruction_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_LOAD_RECONSTRUCTION,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            # callback=self.load_reconstruction,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_DIALOG_JSON)

    def export_wav_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_EXPORT_WAV,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            # callback=self.export_wav,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_DIALOG_WAV)

    def _on_instruction_selected(
        self, generator_class_name: str, instruction, fragment: LibraryFragment, library_config: LibraryConfig
    ) -> None:
        self.instruction_panel.display_instruction(generator_class_name, instruction, fragment, library_config)

    def _on_reconstruction_selected(self, reconstruction_data: ReconstructionData) -> None:
        self.reconstruction_panel.display_reconstruction(reconstruction_data)

    def run(self) -> None:
        dpg.start_dearpygui()
        dpg.destroy_context()
