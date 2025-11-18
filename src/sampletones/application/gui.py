import sys
import tkinter
from pathlib import Path
from typing import Callable, Dict, List, Optional

import dearpygui.dearpygui as dpg
from screeninfo import get_monitors

from sampletones._resources import get_icon_path
from sampletones.audio import AudioDeviceManager
from sampletones.configs import LibraryConfig
from sampletones.constants.paths import (
    EXT_FILE_JSON,
    EXT_FILE_RECONSTRUCTION,
    EXT_FILE_WAVE,
    ICON_UNIX_FILENAME,
    ICON_WIN_FILENAME,
)
from sampletones.exceptions import LibraryDisplayError
from sampletones.library import LibraryFragment
from sampletones.typehints import Sender
from sampletones.utils.logger import logger

from .config.manager import ConfigManager
from .constants import (
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
    FLAG_WINDOW_PRIMARY_ENABLED,
    LBL_MENU_EXIT,
    LBL_MENU_EXPORT_RECONSTRUCTION_FTIS,
    LBL_MENU_EXPORT_RECONSTRUCTION_WAV,
    LBL_MENU_FILE,
    LBL_MENU_FULLSCREEN,
    LBL_MENU_LOAD_CONFIG,
    LBL_MENU_LOAD_RECONSTRUCTION,
    LBL_MENU_RECONSTRUCT_DIRECTORY,
    LBL_MENU_RECONSTRUCT_FILE,
    LBL_MENU_SAVE_CONFIG,
    LBL_MENU_VIEW,
    LBL_TAB_LIBRARY,
    LBL_TAB_RECONSTRUCTION,
    MSG_CONFIG_LOADED_SUCCESSFULLY,
    MSG_CONFIG_SAVE_FAILED,
    MSG_CONFIG_SAVED_SUCCESSFULLY,
    MSG_LIBRARY_DISPLAY_ERROR,
    MSG_RECONSTRUCTION_EXPORT_WAV_FAILURE,
    SUF_CENTER_PANEL,
    TAG_BROWSER_PANEL_GROUP,
    TAG_CONFIG_PANEL_GROUP,
    TAG_CONFIG_STATUS_POPUP,
    TAG_LIBRARY_PANEL_GROUP,
    TAG_MENU_RECONSTRUCT_DIRECTORY,
    TAG_MENU_RECONSTRUCT_FILE,
    TAG_MENU_RECONSTRUCTION_EXPORT_FTIS,
    TAG_MENU_RECONSTRUCTION_EXPORT_WAV,
    TAG_MENU_VIEW_FULLSCREEN,
    TAG_RECONSTRUCTOR_PANEL_GROUP,
    TAG_TAB_BAR_MAIN,
    TAG_TAB_LIBRARY,
    TAG_TAB_RECONSTRUCTION,
    TAG_WINDOW_MAIN,
    TITLE_DIALOG_CONFIG_STATUS,
    TITLE_DIALOG_LOAD_CONFIG,
    TITLE_DIALOG_LOAD_RECONSTRUCTION,
    TITLE_DIALOG_RECONSTRUCT_DIRECTORY,
    TITLE_DIALOG_RECONSTRUCT_FILE,
    TITLE_DIALOG_SAVE_CONFIG,
    TITLE_WINDOW_MAIN,
    VAL_DIALOG_DEFAULT_FILENAME_CONFIG,
    VAL_DIALOG_FILE_COUNT_SINGLE,
    VAL_WINDOW_X_POS,
    VAL_WINDOW_Y_POS,
)
from .panels.browser import GUIBrowserPanel
from .panels.config import GUIConfigPanel
from .panels.converter import GUIConverterWindow
from .panels.instruction.details import GUIInstructionDetailsPanel
from .panels.instruction.instruction import GUIInstructionPanel
from .panels.library import GUILibraryPanel
from .panels.reconstruction.details import GUIReconstructionDetailsPanel
from .panels.reconstruction.reconstruction import GUIReconstructionPanel
from .panels.reconstructor import GUIReconstructorPanel
from .reconstruction.data import ReconstructionData
from .utils.dialogs import (
    show_error_dialog,
    show_library_not_loaded_dialog,
    show_modal_dialog,
    show_reconstruction_not_loaded_dialog,
)
from .utils.dpg import dpg_configure_item, dpg_set_value
from .utils.file import file_dialog_handler


class GUI:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.audio_device_manager = AudioDeviceManager()
        self.config_manager = ConfigManager(config_path)

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
        self._is_fullscreen: bool = False
        self._previous_viewport_decorated: Optional[bool] = None
        self._previous_viewport_position: Optional[list[float]] = None
        self._previous_viewport_size: Optional[tuple[int, int]] = None

        self.setup_gui()

    def setup_gui(self) -> None:
        dpg.create_context()
        self.create_main_window()
        self.set_viewport()
        dpg.setup_dearpygui()
        dpg.show_viewport()
        self.set_callbacks()
        self.config_manager.update_gui()
        self.update_menu()

    def set_viewport(self) -> None:
        if sys.platform.startswith("win"):
            icon_filename = ICON_WIN_FILENAME
        else:
            icon_filename = ICON_UNIX_FILENAME

        icon_file_path = get_icon_path(icon_filename)

        dpg.create_viewport(
            title=TITLE_WINDOW_MAIN,
            width=DIM_WINDOW_MAIN_WIDTH,
            height=DIM_WINDOW_MAIN_HEIGHT,
            small_icon=str(icon_file_path),
            large_icon=str(icon_file_path),
            x_pos=VAL_WINDOW_X_POS,
            y_pos=VAL_WINDOW_Y_POS,
            decorated=True,
        )

        self._is_fullscreen = False
        self._previous_viewport_decorated = dpg.is_viewport_decorated()

    def set_callbacks(self) -> None:
        self.config_manager.add_config_change_callback(self.library_panel.update_status)
        self.config_manager.add_config_change_callback(self.update_menu)
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
            on_cancelled=self.browser_panel.refresh,
        )

        self.instruction_panel.set_callbacks(
            on_display_instruction_details=self.instruction_details_panel.display_instruction,
            on_clear_instruction_details=self.instruction_details_panel.clear_display,
        )

        self.reconstruction_panel.set_callbacks(
            on_export_wav=self._export_reconstruction_wav_dialog,
            on_display_reconstruction_details=self.reconstruction_details_panel.display_reconstruction,
            on_clear_reconstruction_details=self.reconstruction_details_panel.clear_display,
        )

        self.reconstruction_details_panel.set_callbacks(
            on_instrument_export=self.reconstruction_panel.export_reconstruction_fti_dialog,
            on_instruments_export=self.reconstruction_panel.export_reconstruction_ftis_dialog,
        )

    def create_main_window(self) -> None:
        with dpg.window(label=TITLE_WINDOW_MAIN, tag=TAG_WINDOW_MAIN):
            self.create_menu_bar()
            self.create_tabs()
            # dpg.add_key_press_handler(key=dpg.mvKey_Escape, callback=self._on_key_escape)
            # dpg.add_key_press_handler(key=dpg.mvKey_F11, callback=self._on_toggle_fullscreen)

        dpg.set_primary_window(TAG_WINDOW_MAIN, FLAG_WINDOW_PRIMARY_ENABLED)

    def create_menu_bar(self) -> None:
        with dpg.menu_bar():
            with dpg.menu(label=LBL_MENU_FILE):
                dpg.add_menu_item(label=LBL_MENU_SAVE_CONFIG, callback=self._save_config_dialog)
                dpg.add_menu_item(label=LBL_MENU_LOAD_CONFIG, callback=self._load_config_dialog)
                dpg.add_separator()
                dpg.add_menu_item(label=LBL_MENU_LOAD_RECONSTRUCTION, callback=self._load_reconstruction_dialog)
                dpg.add_menu_item(
                    tag=TAG_MENU_RECONSTRUCT_FILE,
                    label=LBL_MENU_RECONSTRUCT_FILE,
                    callback=self._reconstruct_file_dialog,
                    enabled=self._is_library_loaded(),
                )
                dpg.add_menu_item(
                    tag=TAG_MENU_RECONSTRUCT_DIRECTORY,
                    label=LBL_MENU_RECONSTRUCT_DIRECTORY,
                    callback=self._reconstruct_directory_dialog,
                    enabled=self._is_library_loaded(),
                )
                dpg.add_separator()
                dpg.add_menu_item(
                    tag=TAG_MENU_RECONSTRUCTION_EXPORT_WAV,
                    label=LBL_MENU_EXPORT_RECONSTRUCTION_WAV,
                    callback=self._export_reconstruction_wav_dialog,
                    enabled=self._is_reconstruction_loaded(),
                )
                dpg.add_menu_item(
                    tag=TAG_MENU_RECONSTRUCTION_EXPORT_FTIS,
                    label=LBL_MENU_EXPORT_RECONSTRUCTION_FTIS,
                    callback=self._export_reconstruction_ftis_dialog,
                    enabled=self._is_reconstruction_loaded(),
                )
                dpg.add_separator()
                dpg.add_menu_item(label=LBL_MENU_EXIT, callback=self._exit_application)
            with dpg.menu(label=LBL_MENU_VIEW):
                dpg.add_menu_item(
                    tag=TAG_MENU_VIEW_FULLSCREEN,
                    label=LBL_MENU_FULLSCREEN,
                    callback=self._toggle_fullscreen,
                    check=True,
                )

    def update_menu(self) -> None:
        library_loaded = self._is_library_loaded()
        reconstruction_loaded = self._is_reconstruction_loaded()

        dpg_configure_item(TAG_MENU_RECONSTRUCT_FILE, enabled=library_loaded)
        dpg_configure_item(TAG_MENU_RECONSTRUCT_DIRECTORY, enabled=library_loaded)
        dpg_configure_item(TAG_MENU_RECONSTRUCTION_EXPORT_WAV, enabled=reconstruction_loaded)
        dpg_configure_item(TAG_MENU_RECONSTRUCTION_EXPORT_FTIS, enabled=reconstruction_loaded)
        dpg_set_value(TAG_MENU_VIEW_FULLSCREEN, self._is_fullscreen)
        dpg_configure_item(TAG_MENU_VIEW_FULLSCREEN, check=self._is_fullscreen)

    def create_tabs(self) -> None:
        with dpg.tab_bar(tag=TAG_TAB_BAR_MAIN):
            self.create_library_tab()
            self.create_reconstruction_tab()

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
            logger.error_with_traceback(exception, f"Failed to save config to {filepath}")
            show_error_dialog(exception, MSG_CONFIG_SAVE_FAILED)

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
            logger.error_with_traceback(exception, f"Failed to load config from {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTION_EXPORT_WAV_FAILURE)

    def _reconstruct_file_dialog(self) -> None:
        if not self._check_if_library_loaded():
            return

        with dpg.file_dialog(
            label=TITLE_DIALOG_RECONSTRUCT_FILE,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._handle_reconstruct_file,
            file_count=VAL_DIALOG_FILE_COUNT_SINGLE,
        ):
            dpg.add_file_extension(EXT_FILE_WAVE)

    def _reconstruct_directory_dialog(self) -> None:
        if not self._check_if_library_loaded():
            return

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
            dpg.add_file_extension(EXT_FILE_RECONSTRUCTION)

    def _show_config_status_dialog(self, message: str) -> None:
        def content_builder(parent: str) -> None:
            dpg.add_text(message, parent=parent)

        show_modal_dialog(
            tag=TAG_CONFIG_STATUS_POPUP,
            title=TITLE_DIALOG_CONFIG_STATUS,
            content=content_builder,
        )

    def _on_instruction_selected(
        self,
        generator_class_name: str,
        instruction,
        fragment: LibraryFragment,
        library_config: LibraryConfig,
    ) -> None:
        try:
            self.instruction_panel.display_instruction(
                generator_class_name,
                instruction,
                fragment,
                library_config,
            )
        except LibraryDisplayError as exception:
            show_error_dialog(exception, MSG_LIBRARY_DISPLAY_ERROR)

    def _on_reconstruction_selected(self, reconstruction_data: ReconstructionData) -> None:
        self.reconstruction_panel.display_reconstruction(reconstruction_data)
        self.update_menu()
        self.audio_device_manager.stop()

    def _export_reconstruction_wav_dialog(self) -> None:
        if self._check_if_reconstruction_loaded():
            self.reconstruction_panel.export_reconstruction_wav_dialog()

    def _export_reconstruction_ftis_dialog(self) -> None:
        if self._check_if_reconstruction_loaded():
            self.reconstruction_panel.export_reconstruction_ftis_dialog()

    def _check_if_reconstruction_loaded(self) -> bool:
        if not self._is_reconstruction_loaded():
            logger.warning("No reconstruction loaded; cannot proceed")
            show_reconstruction_not_loaded_dialog()
            return False

        return True

    @staticmethod
    def _get_monitors() -> List[Dict]:
        monitors: List[Dict] = []
        for monitor in get_monitors():
            monitors.append(
                {
                    "x": int(monitor.x),
                    "y": int(monitor.y),
                    "width": int(monitor.width),
                    "height": int(monitor.height),
                }
            )

        return monitors

    def _monitor_for_position(self, x: float, y: float) -> Optional[Dict]:
        monitors = self._get_monitors()
        px = float(x)
        py = float(y)

        for monitor in monitors:
            if (
                px >= monitor["x"]
                and px < (monitor["x"] + monitor["width"])
                and py >= monitor["y"]
                and py < (monitor["y"] + monitor["height"])
            ):
                return monitor

        return monitors[0] if monitors else None

    def _on_key_escape(
        self,
        sender: Sender,
        app_data: Optional[object] = None,
        user_data: Optional[object] = None,
    ) -> None:
        if self._is_fullscreen:
            self._toggle_fullscreen(sender, app_data, user_data)

    def _on_toggle_fullscreen(
        self,
        sender: Sender,
        app_data: Optional[object] = None,
        user_data: Optional[object] = None,
    ) -> None:
        self._toggle_fullscreen(sender, app_data, user_data)

    def _is_reconstruction_loaded(self) -> bool:
        return self.reconstruction_panel.is_loaded()

    def _is_library_loaded(self) -> bool:
        return self.library_panel.is_loaded()

    def _check_if_library_loaded(self) -> bool:
        if not self._is_library_loaded():
            key = self.config_manager.key
            logger.warning(f"Library {key} is not loaded; cannot proceed")
            show_library_not_loaded_dialog(key)
            return False

        return True

    @file_dialog_handler
    def _handle_reconstruct_file(self, filepath: Path) -> None:
        self.converter_window.show(filepath, is_file=True)

    @file_dialog_handler
    def _handle_reconstruct_directory(self, directory_path: Path) -> None:
        self.converter_window.show(directory_path, is_file=False)

    @file_dialog_handler
    def _handle_load_reconstruction(self, filepath: Path) -> None:
        self.browser_panel.load_and_display_reconstruction(filepath)
        dpg_set_value(TAG_TAB_BAR_MAIN, TAG_TAB_RECONSTRUCTION)

    def _on_reconstruction_loaded(self, filepath: Path) -> None:
        self.browser_panel.refresh()
        self.browser_panel.load_and_display_reconstruction(filepath)
        dpg_set_value(TAG_TAB_BAR_MAIN, TAG_TAB_RECONSTRUCTION)
        self.audio_device_manager.stop()

    def _exit_application(self) -> None:
        if self.converter_window and self.converter_window.converter:
            self.converter_window.converter.cleanup()
        dpg.stop_dearpygui()

    def _enable_fullscreen(self) -> None:
        previous_decorated = dpg.is_viewport_decorated()
        dpg.set_viewport_decorated(False)
        self._previous_viewport_decorated = previous_decorated
        self._previous_viewport_position = list(dpg.get_viewport_pos())
        self._previous_viewport_size = (int(dpg.get_viewport_width()), int(dpg.get_viewport_height()))

        monitor_x = VAL_WINDOW_X_POS
        monitor_y = VAL_WINDOW_Y_POS
        monitor_width = None
        monitor_height = None

        monitor = None
        if self._previous_viewport_position is not None:
            monitor = self._monitor_for_position(
                self._previous_viewport_position[0], self._previous_viewport_position[1]
            )

        if monitor is not None:
            monitor_x = int(monitor.get("x", VAL_WINDOW_X_POS))
            monitor_y = int(monitor.get("y", VAL_WINDOW_Y_POS))
            monitor_width = int(
                monitor.get(
                    "width",
                    self._previous_viewport_size[0] if self._previous_viewport_size else DIM_WINDOW_MAIN_WIDTH,
                )
            )
            monitor_height = int(
                monitor.get(
                    "height",
                    self._previous_viewport_size[1] if self._previous_viewport_size else DIM_WINDOW_MAIN_HEIGHT,
                )
            )
        else:
            _root = tkinter.Tk()
            _root.withdraw()
            monitor_width = int(_root.winfo_screenwidth())
            monitor_height = int(_root.winfo_screenheight())
            _root.destroy()

        dpg.set_viewport_pos([monitor_x, monitor_y])
        dpg.set_viewport_width(monitor_width)
        dpg.set_viewport_height(monitor_height)
        self._is_fullscreen = True

    def _disable_fullscreen(self) -> None:
        if self._previous_viewport_size is not None:
            width, height = self._previous_viewport_size
            dpg.set_viewport_width(width)
            dpg.set_viewport_height(height)
        else:
            dpg.set_viewport_width(DIM_WINDOW_MAIN_WIDTH)
            dpg.set_viewport_height(DIM_WINDOW_MAIN_HEIGHT)

        if self._previous_viewport_position is not None:
            dpg.set_viewport_pos(list(self._previous_viewport_position))
        else:
            dpg.set_viewport_pos([VAL_WINDOW_X_POS, VAL_WINDOW_Y_POS])

        dpg.set_viewport_decorated(True)
        self._is_fullscreen = False
        self._update_fullscreen_menu_item()

    def _toggle_fullscreen(
        self,
        sender: Sender,
        app_data: Optional[object] = None,
        user_data: Optional[object] = None,
    ) -> None:
        if not self._is_fullscreen:
            self._enable_fullscreen()
        else:
            self._disable_fullscreen()

    def _update_fullscreen_menu_item(self) -> None:
        dpg_set_value(TAG_MENU_VIEW_FULLSCREEN, self._is_fullscreen)

    def run(self) -> None:
        try:
            dpg.start_dearpygui()
        finally:
            if self.converter_window and self.converter_window.converter:
                self.converter_window.converter.cleanup()
            self.config_manager.save_config()
            dpg.destroy_context()
