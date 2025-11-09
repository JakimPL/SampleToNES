from pathlib import Path
from typing import Callable

import dearpygui.dearpygui as dpg

from browser.browser.panel import GUIBrowserPanel
from browser.config.manager import ConfigManager
from browser.config.panel import GUIConfigPanel
from browser.converter.window import GUIConverterWindow
from browser.instruction.details import GUIInstructionDetailsPanel
from browser.instruction.panel import GUIInstructionPanel
from browser.library.panel import GUILibraryPanel
from browser.reconstruction.data import ReconstructionData
from browser.reconstruction.details import GUIReconstructionDetailsPanel
from browser.reconstruction.panel import GUIReconstructionPanel
from browser.reconstructor.panel import GUIReconstructorPanel
from browser.utils import file_dialog_handler, show_modal_dialog
from configs.library import LibraryConfig
from constants.browser import (
    DIM_DIALOG_FILE_HEIGHT,
    DIM_DIALOG_FILE_WIDTH,
    DIM_PANEL_INSTRUCTION_DETAILS_WIDTH,
    DIM_PANEL_LEFT_HEIGHT,
    DIM_PANEL_LEFT_WIDTH,
    DIM_PANEL_RECONSTRUCTION_DETAILS_WIDTH,
    DIM_PANEL_RIGHT_HEIGHT,
    DIM_PANEL_RIGHT_WIDTH,
    DIM_WINDOW_MAIN_HEIGHT,
    DIM_WINDOW_MAIN_WIDTH,
    EXT_FILE_JSON,
    EXT_FILE_WAV,
    FLAG_WINDOW_PRIMARY_ENABLED,
    LBL_MENU_EXIT,
    LBL_MENU_EXPORT_RECONSTRUCTION_FTI,
    LBL_MENU_EXPORT_RECONSTRUCTION_WAV,
    LBL_MENU_FILE,
    LBL_MENU_LOAD_CONFIG,
    LBL_MENU_LOAD_RECONSTRUCTION,
    LBL_MENU_RECONSTRUCT_DIRECTORY,
    LBL_MENU_RECONSTRUCT_FILE,
    LBL_MENU_SAVE_CONFIG,
    LBL_TAB_LIBRARY,
    LBL_TAB_RECONSTRUCTION,
    MSG_CONFIG_LOADED_SUCCESSFULLY,
    MSG_CONFIG_SAVED_SUCCESSFULLY,
    SUF_CENTER_PANEL,
    TAG_BROWSER_PANEL_GROUP,
    TAG_CONFIG_PANEL_GROUP,
    TAG_CONFIG_STATUS_POPUP,
    TAG_LIBRARY_PANEL_GROUP,
    TAG_RECONSTRUCTOR_PANEL_GROUP,
    TAG_TAB_BAR_MAIN,
    TAG_TAB_LIBRARY,
    TAG_TAB_RECONSTRUCTION,
    TAG_WINDOW_MAIN,
    TITLE_DIALOG_CONFIG_STATUS,
    TITLE_DIALOG_EXPORT_FTI_DIRECTORY,
    TITLE_DIALOG_LOAD_CONFIG,
    TITLE_DIALOG_LOAD_RECONSTRUCTION,
    TITLE_DIALOG_RECONSTRUCT_DIRECTORY,
    TITLE_DIALOG_RECONSTRUCT_FILE,
    TITLE_DIALOG_SAVE_CONFIG,
    TITLE_WINDOW_MAIN,
    TPL_RECONSTRUCTION_EXPORT_ERROR,
    VAL_DIALOG_DEFAULT_FILENAME_CONFIG,
    VAL_DIALOG_FILE_COUNT_SINGLE,
)
from library.data import LibraryFragment
from utils.audio.manager import AudioDeviceManager
from utils.logger import logger


class GUI:
    def __init__(self) -> None:
        self.audio_device_manager = AudioDeviceManager()
        self.config_manager = ConfigManager()

        self.config_panel: GUIConfigPanel = GUIConfigPanel(self.config_manager)
        self.library_panel: GUILibraryPanel = GUILibraryPanel(self.config_manager)
        self.instruction_panel: GUIInstructionPanel = GUIInstructionPanel(self.audio_device_manager)
        self.instruction_details_panel: GUIInstructionDetailsPanel = GUIInstructionDetailsPanel()

        self.reconstructor_panel: GUIReconstructorPanel = GUIReconstructorPanel(self.config_manager)
        self.browser_panel: GUIBrowserPanel = GUIBrowserPanel(self.config_manager)
        self.reconstruction_panel: GUIReconstructionPanel = GUIReconstructionPanel(
            self.config_manager, self.audio_device_manager
        )
        self.reconstruction_details_panel: GUIReconstructionDetailsPanel = GUIReconstructionDetailsPanel()

        self.converter_window: GUIConverterWindow = GUIConverterWindow(self.config_manager)

        self.setup_gui()

    def setup_gui(self) -> None:
        dpg.create_context()
        self.create_main_window()
        dpg.create_viewport(title=TITLE_WINDOW_MAIN, width=DIM_WINDOW_MAIN_WIDTH, height=DIM_WINDOW_MAIN_HEIGHT)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        self.set_callbacks()
        self.config_manager.update_gui()

    def set_callbacks(self) -> None:
        self.config_manager.add_config_change_callback(self.library_panel.update_status)
        self.config_manager.add_config_change_callback(self.config_panel.update_gui_from_config)
        self.config_manager.add_config_change_callback(self.reconstructor_panel.update_gui_from_config)
        self.config_panel.set_callbacks(on_update_library_directory=self.library_panel.refresh)
        self.library_panel.set_callbacks(
            on_instruction_selected=self._on_instruction_selected,
            on_apply_library_config=self.config_panel.apply_library_config,
        )
        self.reconstructor_panel.set_callbacks(
            on_update_library_directory=self.browser_panel.refresh,
        )
        self.browser_panel.set_callbacks(
            on_reconstruction_selected=self._on_reconstruction_selected,
            on_reconstruct_file=self._reconstruct_file_dialog,
            on_reconstruct_directory=self._reconstruct_directory_dialog,
        )

        self.converter_window.set_callbacks(
            on_load_file=self._on_reconstruction_loaded,
            on_load_directory=self.browser_panel.refresh,
        )

        self.instruction_panel.set_callbacks(
            on_display_instruction_details=self.instruction_details_panel.display_instruction,
            on_clear_instruction_details=self.instruction_details_panel.clear_display,
        )

        self.reconstruction_panel.set_callbacks(
            on_export_wav=self._export_reconstruction_to_wav,
            on_display_reconstruction_details=self.reconstruction_details_panel.display_reconstruction,
            on_clear_reconstruction_details=self.reconstruction_details_panel.clear_display,
        )

        self.reconstruction_details_panel.set_callback(
            on_instrument_export=self.reconstruction_panel._handle_instrument_export,
        )

    def create_main_window(self) -> None:
        with dpg.window(label=TITLE_WINDOW_MAIN, tag=TAG_WINDOW_MAIN):
            with dpg.menu_bar():
                with dpg.menu(label=LBL_MENU_FILE):
                    dpg.add_menu_item(label=LBL_MENU_SAVE_CONFIG, callback=self._save_config_dialog)
                    dpg.add_menu_item(label=LBL_MENU_LOAD_CONFIG, callback=self._load_config_dialog)
                    dpg.add_separator()
                    dpg.add_menu_item(label=LBL_MENU_RECONSTRUCT_FILE, callback=self._reconstruct_file_dialog)
                    dpg.add_menu_item(label=LBL_MENU_RECONSTRUCT_DIRECTORY, callback=self._reconstruct_directory_dialog)
                    dpg.add_menu_item(label=LBL_MENU_LOAD_RECONSTRUCTION, callback=self._load_reconstruction_dialog)
                    dpg.add_separator()
                    dpg.add_menu_item(
                        label=LBL_MENU_EXPORT_RECONSTRUCTION_WAV, callback=self._export_reconstruction_to_wav
                    )
                    dpg.add_menu_item(
                        label=LBL_MENU_EXPORT_RECONSTRUCTION_FTI, callback=self._export_reconstruction_fti_dialog
                    )
                    dpg.add_separator()
                    dpg.add_menu_item(label=LBL_MENU_EXIT, callback=self._exit_application)

            with dpg.tab_bar(tag=TAG_TAB_BAR_MAIN):
                self.create_library_tab()
                self.create_reconstruction_tab()

        dpg.set_primary_window(TAG_WINDOW_MAIN, FLAG_WINDOW_PRIMARY_ENABLED)

    @staticmethod
    def create_layout(
        label: str,
        tab_tag: str,
        left_content_builder: Callable[[], None],
        center_content_builder: Callable[[], None],
        right_content_builder: Callable[[], None],
        left_panel_height: int,
        right_panel_height: int,
        left_panel_width: int = DIM_PANEL_LEFT_WIDTH,
        right_panel_width: int = DIM_PANEL_RIGHT_WIDTH,
    ) -> None:
        with dpg.tab(tag=tab_tag, label=label):
            with dpg.table(
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
                borders_innerV=False,
                borders_outerV=False,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        width=left_panel_width,
                        height=left_panel_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        left_content_builder()

                    with dpg.child_window(
                        tag=f"{tab_tag}{SUF_CENTER_PANEL}",
                        no_scroll_with_mouse=True,
                    ):
                        center_content_builder()

                    with dpg.child_window(
                        width=right_panel_width,
                        height=right_panel_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        right_content_builder()

    def create_library_tab(self) -> None:
        self.create_layout(
            label=LBL_TAB_LIBRARY,
            tab_tag=TAG_TAB_LIBRARY,
            left_content_builder=self._create_library_left_panel,
            center_content_builder=lambda: self.instruction_panel.create_panel(),
            right_content_builder=lambda: self.instruction_details_panel.create_panel(),
            left_panel_height=DIM_PANEL_LEFT_HEIGHT,
            right_panel_height=DIM_PANEL_RIGHT_HEIGHT,
            right_panel_width=DIM_PANEL_INSTRUCTION_DETAILS_WIDTH,
        )
        self.library_panel.initialize_libraries()

    def create_reconstruction_tab(self) -> None:
        self.create_layout(
            label=LBL_TAB_RECONSTRUCTION,
            tab_tag=TAG_TAB_RECONSTRUCTION,
            left_content_builder=self._create_reconstruction_left_panel,
            center_content_builder=lambda: self.reconstruction_panel.create_panel(),
            right_content_builder=lambda: self.reconstruction_details_panel.create_panel(),
            left_panel_height=DIM_PANEL_LEFT_HEIGHT,
            right_panel_height=DIM_PANEL_RIGHT_HEIGHT,
            right_panel_width=DIM_PANEL_RECONSTRUCTION_DETAILS_WIDTH,
        )
        self.browser_panel.initialize_tree()

    def _create_library_left_panel(self) -> None:
        with dpg.group(tag=TAG_CONFIG_PANEL_GROUP):
            self.config_panel.create_panel()

        with dpg.group(tag=TAG_LIBRARY_PANEL_GROUP):
            self.library_panel.create_panel()

    def _create_reconstruction_left_panel(self) -> None:
        with dpg.group(tag=TAG_RECONSTRUCTOR_PANEL_GROUP):
            self.reconstructor_panel.create_panel()

        with dpg.group(tag=TAG_BROWSER_PANEL_GROUP):
            self.browser_panel.create_panel()

    def _save_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_SAVE_CONFIG,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._handle_save_config,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
            default_filename=VAL_DIALOG_DEFAULT_FILENAME_CONFIG,
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    @file_dialog_handler
    def _handle_save_config(self, filepath: Path) -> None:
        try:
            self.config_manager.save_config_to_file(filepath)
            self._show_config_status_dialog(MSG_CONFIG_SAVED_SUCCESSFULLY)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(f"Failed to save config to {filepath}", exception)
            self._show_config_status_dialog(TPL_RECONSTRUCTION_EXPORT_ERROR.format(str(exception)))

    def _load_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_LOAD_CONFIG,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._handle_load_config,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    @file_dialog_handler
    def _handle_load_config(self, filepath: Path) -> None:
        try:
            self.config_manager.load_config_from_file(filepath)
            self._show_config_status_dialog(MSG_CONFIG_LOADED_SUCCESSFULLY)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(f"Failed to load config from {filepath}", exception)
            self._show_config_status_dialog(TPL_RECONSTRUCTION_EXPORT_ERROR.format(str(exception)))

    def _reconstruct_file_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_RECONSTRUCT_FILE,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._handle_reconstruct_file,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_FILE_WAV)

    def _reconstruct_directory_dialog(self) -> None:
        dpg.add_file_dialog(
            label=TITLE_DIALOG_RECONSTRUCT_DIRECTORY,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._handle_reconstruct_directory,
            directory_selector=True,
            show=True,
        )

    def _load_reconstruction_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_LOAD_RECONSTRUCTION,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._handle_load_reconstruction,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    def _export_reconstruction_fti_dialog(self) -> None:
        dpg.add_file_dialog(
            label=TITLE_DIALOG_EXPORT_FTI_DIRECTORY,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            directory_selector=True,
            show=True,
        )

    def _show_config_status_dialog(self, message: str) -> None:
        def content_builder(parent: str) -> None:
            dpg.add_text(message, parent=parent)

        show_modal_dialog(
            tag=TAG_CONFIG_STATUS_POPUP,
            title=TITLE_DIALOG_CONFIG_STATUS,
            content=content_builder,
        )

    def _on_instruction_selected(
        self, generator_class_name: str, instruction, fragment: LibraryFragment, library_config: LibraryConfig
    ) -> None:
        self.instruction_panel.display_instruction(generator_class_name, instruction, fragment, library_config)

    def _on_reconstruction_selected(self, reconstruction_data: ReconstructionData) -> None:
        self.reconstruction_panel.display_reconstruction(reconstruction_data)

    def _export_reconstruction_to_wav(self) -> None:
        self.reconstruction_panel.export_reconstruction_to_wav()

    def _export_reconstruction_to_fti(self) -> None:
        pass  # self.reconstruction_details_panel.export_reconstruction_to_fti()

    @file_dialog_handler
    def _handle_reconstruct_file(self, filepath: Path) -> None:
        self.converter_window.show(filepath, is_file=True)

    @file_dialog_handler
    def _handle_reconstruct_directory(self, directory_path: Path) -> None:
        self.converter_window.show(directory_path, is_file=False)

    @file_dialog_handler
    def _handle_load_reconstruction(self, filepath: Path) -> None:
        self.browser_panel.load_and_display_reconstruction(filepath)
        dpg.set_value(TAG_TAB_BAR_MAIN, TAG_TAB_RECONSTRUCTION)

    def _on_reconstruction_loaded(self, filepath: Path) -> None:
        self.browser_panel.load_and_display_reconstruction(filepath)
        dpg.set_value(TAG_TAB_BAR_MAIN, TAG_TAB_RECONSTRUCTION)

    def _exit_application(self) -> None:
        if self.converter_window and self.converter_window.converter:
            self.converter_window.converter.cleanup()
        dpg.stop_dearpygui()

    def run(self) -> None:
        try:
            dpg.start_dearpygui()
        finally:
            if self.converter_window and self.converter_window.converter:
                self.converter_window.converter.cleanup()
            self.config_manager.save_config()
            dpg.destroy_context()
