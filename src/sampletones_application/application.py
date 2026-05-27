from pathlib import Path
from typing import Any, Optional

import dearpygui.dearpygui as dpg

from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.paths import EXT_FILE_JSON, EXT_FILE_RECONSTRUCTION, EXT_FILES_AUDIO
from sampletones_core.sequencer import Sequencer
from sampletones_shared.exceptions import LoadReconstructionError
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback

from .config.application.manager import ApplicationConfigManager
from .config.manager import ConfigManager
from .constants.general import (
    DIM_DIALOG_HEIGHT_FILE,
    DIM_DIALOG_WIDTH_FILE,
    DIM_STATUS_HEIGHT,
    LBL_BUTTON_GLOBAL_CLOSE,
    LBL_BUTTON_GLOBAL_DISCARD,
    LBL_BUTTON_GLOBAL_EXIT,
    LBL_BUTTON_GLOBAL_OK,
    LBL_MENU_GROUP_CONFIGURATION,
    LBL_MENU_GROUP_GENERAL,
    LBL_MENU_GROUP_PLAYBACK,
    LBL_MENU_GROUP_RECONSTRUCTION,
    LBL_MENU_GROUP_VIEW,
    LBL_MENU_ITEM_CONFIGURATION_LOAD_CONFIG,
    LBL_MENU_ITEM_CONFIGURATION_SAVE_CONFIG,
    LBL_MENU_ITEM_GENERAL_AUDIO_SETTINGS,
    LBL_MENU_ITEM_GENERAL_EXIT,
    LBL_MENU_ITEM_PLAYBACK_AUTOPLAY,
    LBL_MENU_ITEM_PLAYBACK_PAUSE,
    LBL_MENU_ITEM_PLAYBACK_PLAY,
    LBL_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
    LBL_MENU_ITEM_PLAYBACK_RESUME,
    LBL_MENU_ITEM_PLAYBACK_STOP,
    LBL_MENU_ITEM_RECONSTRUCTION_CLOSE,
    LBL_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS,
    LBL_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV,
    LBL_MENU_ITEM_RECONSTRUCTION_LOAD,
    LBL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
    LBL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
    LBL_MENU_ITEM_RECONSTRUCTION_SAVE,
    LBL_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
    LBL_MENU_ITEM_VIEW_FULLSCREEN,
    LBL_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
    MSG_ALL_AUDIO_FORMATS,
    MSG_AUDIO_PLAYBACK_ERROR,
    MSG_CONFIGURATION_LOADED_SUCCESSFULLY,
    MSG_CONFIGURATION_SAVED_SUCCESSFULLY,
    MSG_GLOBAL_CLOSE_UNSAVED_RECONSTRUCTION,
    MSG_GLOBAL_CONFIG_SAVE_FAILED,
    MSG_GLOBAL_EXIT_CONVERSION_IN_PROGRESS,
    MSG_GLOBAL_EXIT_LIBRARY_GENERATION_IN_PROGRESS,
    MSG_GLOBAL_EXIT_UNSAVED_RECONSTRUCTION,
    MSG_GLOBAL_LOAD_UNSAVED_RECONSTRUCTION,
    MSG_GLOBAL_RECONSTRUCTION_SAVE_FAILED,
    MSG_GLOBAL_RECONSTRUCTION_SAVED_SUCCESSFULLY,
    TAG_DIALOG_GLOBAL_CONFIG_STATUS,
    TAG_DIALOG_GLOBAL_EXIT_CONFIRMATION,
    TAG_DIALOG_GLOBAL_RECONSTRUCTION_SAVED,
    TAG_MENU_ITEM_PLAYBACK_AUTOPLAY,
    TAG_MENU_ITEM_PLAYBACK_PLAY,
    TAG_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
    TAG_MENU_ITEM_PLAYBACK_STOP,
    TAG_MENU_ITEM_RECONSTRUCTION_CLOSE,
    TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS,
    TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV,
    TAG_MENU_ITEM_RECONSTRUCTION_LOAD,
    TAG_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
    TAG_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
    TAG_MENU_ITEM_RECONSTRUCTION_SAVE,
    TAG_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
    TAG_MENU_ITEM_VIEW_FULLSCREEN,
    TAG_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
    TAG_MENU_TEXT_FPS,
    TAG_STATUS_WINDOW,
    TAG_TAB_INSTRUCTIONS,
    TAG_TAB_MAIN,
    TAG_TAB_RECONSTRUCTIONS,
    TAG_TABS,
    TAG_WINDOW_MAIN,
    TPL_MENU_TEXT_FPS,
    TTL_DIALOG_CLOSE_UNSAVED_RECONSTRUCTION,
    TTL_DIALOG_CONFIG_STATUS,
    TTL_DIALOG_EXIT_CONFIRMATION,
    TTL_DIALOG_LOAD_CONFIG,
    TTL_DIALOG_LOAD_UNSAVED_RECONSTRUCTION,
    TTL_DIALOG_RECONSTRUCT_DIRECTORY,
    TTL_DIALOG_RECONSTRUCT_FILE,
    TTL_DIALOG_RECONSTRUCTION_SAVED,
    TTL_DIALOG_SAVE_CONFIG,
    TTL_DIALOG_SAVE_RECONSTRUCTION,
    TTL_WINDOW_MAIN,
    VAL_DIALOG_GLOBAL_DEFAULT_CONFIG_FILENAME,
    VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
    VAL_PRIORITY_UPDATE_STATUS,
    VAL_WINDOW_PRIMARY,
)
from .constants.reconstructions import (
    MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_AUDIO_FILE_NOT_FOUND,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED,
    TTL_DIALOG_LOAD_RECONSTRUCTION,
)
from .coordinators.instructions import InstructionsTabCoordinator
from .coordinators.main import MainTabCoordinator
from .coordinators.reconstructions import ReconstructionsTabCoordinator
from .coordinators.sequencer import SequencerTabCoordinator
from .elements.fonts.registry import FontRegistry
from .elements.status import GUIStatusBar
from .library.manager import InstructionsLibraryManager
from .panels.settings import GUIAudioSettingsWindow
from .reconstruction.browser import BrowserManager
from .reconstruction.manager import ReconstructionManager
from .reconstruction.regenerator import Regenerator
from .themes.default import DefaultTheme
from .themes.fps import FPSTimerTheme
from .utils.callbacks.queue import CallbackQueue
from .utils.dialogs import (
    show_confirmation_dialog,
    show_error_dialog,
    show_file_not_found_dialog,
    show_info_dialog,
    show_modal_dialog,
    show_reconstruction_not_loaded_dialog,
    show_save_confirmation_dialog,
)
from .utils.dpg import dpg_configure_item, dpg_set_value
from .utils.file import file_dialog_handler
from .utils.fps import FPSTimer
from .utils.shortcuts.keys import Modifier
from .utils.shortcuts.manager import ShortcutManager
from .utils.shortcuts.shortcut import Shortcut, ShortcutId
from .viewport import ViewportManager


class Application:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.audio_device_manager: AudioDeviceManager = AudioDeviceManager()
        self.config_manager = ConfigManager(config_path)
        self.application_config_manager = ApplicationConfigManager()
        self.shortcut_manager: ShortcutManager = ShortcutManager()

        self.library_manager = InstructionsLibraryManager(self.config_manager)
        self.browser_manager = BrowserManager(self.config_manager)
        self.reconstruction_manager = ReconstructionManager()
        self.regenerator: Regenerator = Regenerator(self.reconstruction_manager)
        self.sequencer: Sequencer = Sequencer()

        self.fps_timer: FPSTimer = FPSTimer()

        self.audio_settings_window: GUIAudioSettingsWindow = GUIAudioSettingsWindow(self.audio_device_manager)
        self.status_bar = GUIStatusBar()
        self.theme = DefaultTheme()
        self.fps_theme = FPSTimerTheme()

        self._unsaved_reconstruction_changes: bool = False
        self._reconstruction_name: Optional[str] = None

        self._viewport_manager = ViewportManager(
            self.application_config_manager,
            self.theme,
            on_fullscreen_state_changed=self._update_fullscreen_menu_item,
        )

        self._main_tab = MainTabCoordinator(
            config_manager=self.config_manager,
            application_config_manager=self.application_config_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            library_manager=self.library_manager,
            on_reconstruct_file=self._reconstruct_file,
            on_reconstruct_directory=self._reconstruct_directory,
            on_load_reconstruction=self._load_reconstruction_with_confirmation,
            on_load_library=self._load_library,
            is_generation_in_progress=self._is_generation_in_progress,
        )

        self._reconstructions_tab = ReconstructionsTabCoordinator(
            config_manager=self.config_manager,
            application_config_manager=self.application_config_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            reconstruction_manager=self.reconstruction_manager,
            browser_manager=self.browser_manager,
            on_load_reconstruction_with_confirmation=self._load_reconstruction_with_confirmation,
            on_reconstruction_loaded=self._on_reconstruction_loaded,
            on_reconstruct_file=self._reconstruct_file_dialog,
            on_reconstruct_directory=self._reconstruct_directory_dialog,
            on_change_audio_state=self._update_menu,
            on_reconstruction_instrument_updated=self.regenerator.regenerate,
        )

        self._instructions_tab = InstructionsTabCoordinator(
            config_manager=self.config_manager,
            application_config_manager=self.application_config_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            library_manager=self.library_manager,
            on_audio_state_changed=self._update_menu,
        )

        self._sequencer_tab = SequencerTabCoordinator(
            config_manager=self.config_manager,
            application_config_manager=self.application_config_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            browser_manager=self.browser_manager,
        )

        self._setup_gui()
        self._load_settings()

    def _load_settings(self) -> None:
        audio_device = self.application_config_manager.current_audio_device
        buffer_size = self.application_config_manager.current_buffer_size
        self.audio_device_manager.set_current_device(audio_device)
        self.audio_device_manager.set_buffer_size(buffer_size)

    def _setup_gui(self) -> None:
        dpg.create_context()
        self._set_fonts()
        self._register_shortcuts()
        self._set_default_theme()
        self._viewport_manager.create_viewport()
        self._setup_dearpygui()
        self._set_callbacks()
        self._setup_handlers()
        self._create_main_window()
        self._main_tab.emit_initial_view()
        self.config_manager.update_gui()
        self._update_menu()
        self._restore_current_items()
        self._start_callback_worker()
        dpg.set_exit_callback(self._on_close)

    def _start_callback_worker(self) -> None:
        CallbackQueue.start()

    def _setup_dearpygui(self) -> None:
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.render_dearpygui_frame()

    def _update_viewport_title(self, name: Optional[str] = None) -> None:
        if name is not None:
            self._reconstruction_name = name

        self._viewport_manager.update_title(self._reconstruction_name, self._unsaved_reconstruction_changes)

    def _set_fonts(self) -> None:
        FontRegistry.register_fonts()

    def _set_default_theme(self) -> None:
        self.theme.bind()

    def _register_shortcuts(self) -> None:
        self.shortcut_manager.register(
            ShortcutId.SAVE_RECONSTRUCTION,
            Shortcut(dpg.mvKey_S, (Modifier.CTRL,)),
            self._save_reconstruction,
        )
        self.shortcut_manager.register(
            ShortcutId.SAVE_RECONSTRUCTION_AS,
            Shortcut(dpg.mvKey_S, (Modifier.CTRL, Modifier.SHIFT)),
            self._save_reconstruction_as_dialog,
        )
        self.shortcut_manager.register(
            ShortcutId.LOAD_RECONSTRUCTION,
            Shortcut(dpg.mvKey_O, (Modifier.CTRL,)),
            self._load_reconstruction_with_confirmation,
        )
        self.shortcut_manager.register(
            ShortcutId.CLOSE_RECONSTRUCTION,
            Shortcut(dpg.mvKey_W, (Modifier.CTRL,)),
            self._close_reconstruction_with_confirmation,
        )
        self.shortcut_manager.register(
            ShortcutId.SAVE_CONFIGURATION,
            Shortcut(dpg.mvKey_S, (Modifier.CTRL, Modifier.ALT)),
            self._save_config_dialog,
        )
        self.shortcut_manager.register(
            ShortcutId.LOAD_CONFIGURATION,
            Shortcut(dpg.mvKey_O, (Modifier.CTRL, Modifier.ALT)),
            self._load_config_dialog,
        )
        self.shortcut_manager.register(
            ShortcutId.AUDIO_SETTINGS,
            Shortcut(dpg.mvKey_A, (Modifier.CTRL,)),
            self._open_audio_settings,
        )
        self.shortcut_manager.register(
            ShortcutId.EXIT,
            Shortcut(dpg.mvKey_F4, (Modifier.ALT,)),
            self._on_close,
        )
        self.shortcut_manager.register(
            ShortcutId.RECONSTRUCT_FILE,
            Shortcut(dpg.mvKey_R, (Modifier.CTRL,)),
            self._reconstruct_file_dialog,
        )
        self.shortcut_manager.register(
            ShortcutId.RECONSTRUCT_DIRECTORY,
            Shortcut(dpg.mvKey_R, (Modifier.CTRL, Modifier.SHIFT)),
            self._reconstruct_directory_dialog,
        )
        self.shortcut_manager.register(
            ShortcutId.EXPORT_RECONSTRUCTION_WAV,
            Shortcut(dpg.mvKey_E, (Modifier.CTRL,)),
            self._export_reconstruction_wav_dialog,
        )
        self.shortcut_manager.register(
            ShortcutId.EXPORT_RECONSTRUCTION_FTIS,
            Shortcut(dpg.mvKey_I, (Modifier.CTRL,)),
            self._export_reconstruction_ftis_dialog,
        )
        self.shortcut_manager.register(
            ShortcutId.TOGGLE_FULLSCREEN,
            Shortcut(dpg.mvKey_F11),
            self._toggle_fullscreen,
        )
        self.shortcut_manager.register(
            ShortcutId.TOGGLE_ADVANCED_SETTINGS,
            Shortcut(dpg.mvKey_A, (Modifier.CTRL, Modifier.SHIFT)),
            self._toggle_advanced_settings,
        )
        self.shortcut_manager.register(
            ShortcutId.PLAY,
            Shortcut(dpg.mvKey_Spacebar),
            self._play,
        )
        self.shortcut_manager.register(
            ShortcutId.PLAY_FROM_START,
            Shortcut(dpg.mvKey_Spacebar, (Modifier.SHIFT,)),
            self._play_from_start,
        )
        self.shortcut_manager.register(
            ShortcutId.STOP,
            Shortcut(dpg.mvKey_Spacebar, (Modifier.CTRL,)),
            self._stop,
        )
        self.shortcut_manager.register(
            ShortcutId.TOGGLE_AUTOPLAY,
            Shortcut(dpg.mvKey_P, (Modifier.CTRL,)),
            self._toggle_autoplay,
        )

        self.shortcut_manager.bind_all()

    def _set_callbacks(self) -> None:
        self.config_manager.add_config_change_callback(self._update_menu)

        self.audio_device_manager.set_callbacks(on_playback_error=self._on_playback_error)
        self.reconstruction_manager.set_callbacks(
            on_reconstruction_loaded=self._on_reconstruction_loaded,
            on_reconstruction_closed=self._on_reconstruction_closed,
        )
        self.regenerator.set_callbacks(on_regeneration_finished=self._on_reconstruction_updated)

        self._main_tab.converter_logic.on_load_file = self._on_converted_reconstruction_loaded
        self._main_tab.converter_logic.on_load_directory = self._reconstructions_tab.refresh_browser
        self._main_tab.converter_logic.on_cancelled = self._reconstructions_tab.refresh_browser
        self._main_tab.converter_logic.generate_library = self._instructions_tab.ensure_library_loaded

    def _setup_handlers(self) -> None:
        self.shortcut_manager.setup_focus_handler()

    def _create_main_window(self) -> None:
        with dpg.window(
            label=TTL_WINDOW_MAIN,
            tag=TAG_WINDOW_MAIN,
        ):
            self._create_menu_bar()
            self._create_tabs()
            self._create_status_bar()

        dpg.set_primary_window(TAG_WINDOW_MAIN, VAL_WINDOW_PRIMARY)

    def _create_menu_bar(self) -> None:
        with dpg.menu_bar():
            with dpg.menu(label=LBL_MENU_GROUP_GENERAL):
                self.shortcut_manager.add_menu_item(
                    ShortcutId.AUDIO_SETTINGS,
                    label=LBL_MENU_ITEM_GENERAL_AUDIO_SETTINGS,
                )
                dpg.add_separator()
                self.shortcut_manager.add_menu_item(
                    ShortcutId.EXIT,
                    label=LBL_MENU_ITEM_GENERAL_EXIT,
                )
            with dpg.menu(label=LBL_MENU_GROUP_RECONSTRUCTION):
                self.shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_SAVE,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_SAVE,
                    enabled=self._is_reconstruction_loaded(),
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_RECONSTRUCTION_AS,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
                    enabled=self._is_reconstruction_loaded(),
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.CLOSE_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_CLOSE,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_CLOSE,
                    enabled=self._is_reconstruction_loaded(),
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.LOAD_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_LOAD,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_LOAD,
                    enabled=not self._is_reconstruction_loaded(),
                )
                dpg.add_separator()
                self.shortcut_manager.add_menu_item(
                    ShortcutId.RECONSTRUCT_FILE,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.RECONSTRUCT_DIRECTORY,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
                )
                dpg.add_separator()
                self.shortcut_manager.add_menu_item(
                    ShortcutId.EXPORT_RECONSTRUCTION_WAV,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV,
                    enabled=self._is_reconstruction_loaded(),
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.EXPORT_RECONSTRUCTION_FTIS,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS,
                    enabled=self._is_reconstruction_loaded(),
                )
            with dpg.menu(label=LBL_MENU_GROUP_CONFIGURATION):
                self.shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_CONFIGURATION,
                    label=LBL_MENU_ITEM_CONFIGURATION_SAVE_CONFIG,
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.LOAD_CONFIGURATION,
                    label=LBL_MENU_ITEM_CONFIGURATION_LOAD_CONFIG,
                )
            with dpg.menu(label=LBL_MENU_GROUP_PLAYBACK):
                self.shortcut_manager.add_menu_item(
                    ShortcutId.PLAY,
                    tag=TAG_MENU_ITEM_PLAYBACK_PLAY,
                    label=self._get_play_label(),
                    enabled=self._is_play_or_pause_enabled(),
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.PLAY_FROM_START,
                    tag=TAG_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
                    label=LBL_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
                    enabled=self._is_play_or_pause_enabled(),
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.STOP,
                    tag=TAG_MENU_ITEM_PLAYBACK_STOP,
                    label=LBL_MENU_ITEM_PLAYBACK_STOP,
                    enabled=self._is_stop_enabled(),
                )
                dpg.add_separator()
                self.shortcut_manager.add_menu_item(
                    ShortcutId.TOGGLE_AUTOPLAY,
                    tag=TAG_MENU_ITEM_PLAYBACK_AUTOPLAY,
                    label=LBL_MENU_ITEM_PLAYBACK_AUTOPLAY,
                    check=True,
                )
            with dpg.menu(label=LBL_MENU_GROUP_VIEW):
                self.shortcut_manager.add_menu_item(
                    ShortcutId.TOGGLE_ADVANCED_SETTINGS,
                    tag=TAG_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
                    label=LBL_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
                    check=True,
                )
                self.shortcut_manager.add_menu_item(
                    ShortcutId.TOGGLE_FULLSCREEN,
                    tag=TAG_MENU_ITEM_VIEW_FULLSCREEN,
                    label=LBL_MENU_ITEM_VIEW_FULLSCREEN,
                    check=True,
                )

            dpg.add_button(
                label=TPL_MENU_TEXT_FPS.format(fps=0),
                tag=TAG_MENU_TEXT_FPS,
                width=-1,
                enabled=False,
            )

            self.fps_theme.bind_to_item(TAG_MENU_TEXT_FPS)

    def _update_menu(self) -> None:
        self._update_reconstruction_menu_items()
        self._update_playback_menu_items()
        self._update_fullscreen_menu_item()
        self._update_advanced_settings_menu_item()

    def _create_tabs(self) -> None:
        with dpg.child_window(
            height=-DIM_STATUS_HEIGHT,
            border=False,
        ):
            with dpg.tab_bar(
                tag=TAG_TABS,
                callback=self._on_tab_changed,
            ):
                self._main_tab.create_tab()
                self._reconstructions_tab.create_tab()
                self._sequencer_tab.create_tab()
                self._instructions_tab.create_tab()

    def _create_status_bar(self) -> None:
        with dpg.child_window(
            tag=TAG_STATUS_WINDOW,
            parent=TAG_WINDOW_MAIN,
            width=-1,
            height=-1,
            indent=0,
            border=False,
            menubar=True,
        ):
            self.status_bar.create()

    def _on_tab_changed(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        self._update_menu()

    def _restore_current_items(self) -> None:
        current_tab = self.application_config_manager.load_current_tab()
        if dpg.does_alias_exist(current_tab) and dpg.does_item_exist(current_tab):
            dpg.set_value(TAG_TABS, current_tab)

        current_reconstruction = self.application_config_manager.current_reconstruction
        if current_reconstruction is not None:
            if current_reconstruction.exists():
                try:
                    self.reconstruction_manager.load_reconstruction(current_reconstruction)
                except LoadReconstructionError:
                    self.application_config_manager.set_current_reconstruction(None)
            else:
                self.application_config_manager.set_current_reconstruction(None)

    def _save_reconstruction_as_dialog(self) -> None:
        filepath = self.reconstruction_manager.filepath
        if filepath is None:
            return

        with dpg.file_dialog(
            label=TTL_DIALOG_SAVE_RECONSTRUCTION,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_save_reconstruction_as,
            file_count=VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
            default_filename=filepath.name,
            default_path=str(filepath.parent),
        ):
            dpg.add_file_extension(EXT_FILE_RECONSTRUCTION)

    def _save_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=TTL_DIALOG_SAVE_CONFIG,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_save_config,
            file_count=VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
            default_filename=VAL_DIALOG_GLOBAL_DEFAULT_CONFIG_FILENAME,
            default_path=str(self.application_config_manager.get_config_path()),
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    @file_dialog_handler
    def _handle_save_config(self, filepath: Path) -> None:
        try:
            self.config_manager.save_config_to_file(filepath)
            self._show_config_status_dialog(MSG_CONFIGURATION_SAVED_SUCCESSFULLY)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save config to {filepath}")
            show_error_dialog(exception, MSG_GLOBAL_CONFIG_SAVE_FAILED)

        self.application_config_manager.set_config_path(filepath)

    @file_dialog_handler
    def _handle_save_reconstruction_as(self, filepath: Path) -> None:
        try:
            self._save_reconstruction(filepath)
            show_info_dialog(
                TAG_DIALOG_GLOBAL_RECONSTRUCTION_SAVED,
                MSG_GLOBAL_RECONSTRUCTION_SAVED_SUCCESSFULLY,
                TTL_DIALOG_RECONSTRUCTION_SAVED,
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save reconstruction to {filepath}")
            show_error_dialog(exception, MSG_GLOBAL_RECONSTRUCTION_SAVE_FAILED)

        self.application_config_manager.set_reconstruction_path(filepath)

    def _load_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=TTL_DIALOG_LOAD_CONFIG,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_load_config,
            file_count=VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
            default_path=str(self.application_config_manager.get_config_path()),
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    @file_dialog_handler
    def _handle_load_config(self, filepath: Path) -> None:
        try:
            self.config_manager.load_config_from_file(filepath)
            self._show_config_status_dialog(MSG_CONFIGURATION_LOADED_SUCCESSFULLY)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to load config from {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED)

        self.application_config_manager.set_config_path(filepath)

    def _open_audio_settings(self) -> None:
        self.audio_settings_window.show()

    def _reconstruct_file_dialog(self) -> None:
        if self._main_tab.is_converter_running():
            logger.warning("A conversion is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()
        with dpg.file_dialog(
            label=TTL_DIALOG_RECONSTRUCT_FILE,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_reconstruct_file,
            file_count=VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
            default_path=str(self.application_config_manager.get_reconstruction_path()),
        ):
            all_file_extensions = ",".join(EXT_FILES_AUDIO)
            dpg.add_file_extension(f"{MSG_ALL_AUDIO_FORMATS}{{{all_file_extensions}}}", color=(0, 255, 255, 255))
            for extension in EXT_FILES_AUDIO:
                dpg.add_file_extension(extension)

    def _reconstruct_directory_dialog(self) -> None:
        if self._main_tab.is_converter_running():
            logger.warning("A conversion is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()
        dpg.add_file_dialog(
            label=TTL_DIALOG_RECONSTRUCT_DIRECTORY,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_reconstruct_directory,
            directory_selector=True,
            default_path=str(self.application_config_manager.get_reconstruction_path()),
            show=True,
        )

    def _load_reconstruction_dialog(self) -> None:
        with dpg.file_dialog(
            label=TTL_DIALOG_LOAD_RECONSTRUCTION,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_load_reconstruction,
            file_count=VAL_DIALOG_GLOBAL_FILE_COUNT_SINGLE,
            default_path=str(self.application_config_manager.get_reconstruction_path()),
        ):
            dpg.add_file_extension(EXT_FILE_RECONSTRUCTION)

    def _load_reconstruction_with_confirmation(self, filepath: Optional[Path] = None) -> None:
        def load_reconstruction() -> None:
            if filepath is None:
                self._load_reconstruction_dialog()
            else:
                self._reconstructions_tab.load_reconstruction(filepath)

        if self._is_reconstruction_unsaved():
            self._show_save_confirmation_dialog(
                TTL_DIALOG_LOAD_UNSAVED_RECONSTRUCTION,
                MSG_GLOBAL_LOAD_UNSAVED_RECONSTRUCTION,
                on_confirm=load_reconstruction,
                on_save=self._save_reconstruction,
                ok_label=LBL_BUTTON_GLOBAL_DISCARD,
            )
        else:
            load_reconstruction()

    def _show_config_status_dialog(self, message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent)

        show_modal_dialog(
            tag=TAG_DIALOG_GLOBAL_CONFIG_STATUS,
            title=TTL_DIALOG_CONFIG_STATUS,
            content=content,
        )

    def _is_generation_in_progress(self) -> bool:
        return self._main_tab.is_converter_running() or self._instructions_tab.is_library_generating()

    def _export_reconstruction_wav_dialog(self) -> None:
        if self._check_if_reconstruction_loaded():
            self._reconstructions_tab.request_export_wav_dialog()

    def _export_reconstruction_ftis_dialog(self) -> None:
        if self._check_if_reconstruction_loaded():
            self._reconstructions_tab.request_export_instruments_dialog()

    def _check_if_reconstruction_loaded(self) -> bool:
        if not self._is_reconstruction_loaded():
            logger.warning("No reconstruction loaded; cannot proceed")
            show_reconstruction_not_loaded_dialog()
            return False

        return True

    def _is_reconstruction_loaded(self) -> bool:
        return self.reconstruction_manager.is_reconstruction_loaded()

    def _reconstruct_file(self, filepath: Path) -> None:
        self._main_tab.set_input_path(filepath, convert=True)
        self.application_config_manager.set_reconstruction_path(filepath.parent)
        self._set_current_tab(TAG_TAB_MAIN)
        self._update_menu()

    def _load_library(self, filepath: Path) -> None:
        self._instructions_tab.load_library_file(filepath)
        self.config_manager.update_gui()
        self._set_current_tab(TAG_TAB_INSTRUCTIONS)
        self._update_menu()

    @file_dialog_handler
    def _handle_reconstruct_file(self, filepath: Path) -> None:
        self._reconstruct_file(filepath)

    def _reconstruct_directory(self, directory_path: Path) -> None:
        self._main_tab.set_input_path(directory_path, convert=True)
        self.application_config_manager.set_reconstruction_path(directory_path)
        self._set_current_tab(TAG_TAB_MAIN)
        self._update_menu()

    @file_dialog_handler
    def _handle_reconstruct_directory(self, directory_path: Path) -> None:
        self._reconstruct_directory(directory_path)

    def _on_reconstruction_loaded(self) -> None:
        reconstruction_data = self.reconstruction_manager.current_reconstruction
        if reconstruction_data is None:
            raise RuntimeError("No reconstruction is loaded after loading process")

        self.audio_device_manager.stop()
        if not reconstruction_data.reconstruction.audio_filepath.exists():
            show_file_not_found_dialog(
                reconstruction_data.reconstruction.audio_filepath,
                MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_AUDIO_FILE_NOT_FOUND,
            )

        filepath = reconstruction_data.filepath
        self.config_manager.load_library_and_generation_config(reconstruction_data.config)
        self._reconstructions_tab.display_reconstruction()
        self.application_config_manager.set_current_reconstruction(filepath)

        self._set_current_tab(TAG_TAB_RECONSTRUCTIONS)
        self._unsaved_reconstruction_changes = False
        self._update_viewport_title(filepath.stem)
        self._update_menu()

    def _on_playback_error(self, exception: Exception) -> None:
        logger.error_with_traceback(exception, "Playback error occurred")
        show_error_dialog(exception, MSG_AUDIO_PLAYBACK_ERROR)

    @file_dialog_handler
    def _handle_load_reconstruction(self, filepath: Path) -> None:
        self.application_config_manager.set_reconstruction_path(filepath.parent)
        self._reconstructions_tab.load_reconstruction(filepath)

    def _on_reconstruction_updated(self) -> None:
        self._reconstructions_tab.update_reconstruction()
        self._unsaved_reconstruction_changes = True
        self._update_viewport_title()

    def _on_converted_reconstruction_loaded(self, filepath: Path) -> None:
        self._reconstructions_tab.refresh_browser()
        self._load_reconstruction_with_confirmation(filepath)

    def _save_reconstruction(self, filepath: Optional[Path] = None) -> None:
        self.reconstruction_manager.save_reconstruction(filepath)
        self._unsaved_reconstruction_changes = False
        name = filepath.stem if filepath is not None else None
        self._update_viewport_title(name)

    def _close_reconstruction_with_confirmation(self) -> None:
        if self._is_reconstruction_unsaved():
            self._show_save_confirmation_dialog(
                TTL_DIALOG_CLOSE_UNSAVED_RECONSTRUCTION,
                MSG_GLOBAL_CLOSE_UNSAVED_RECONSTRUCTION,
                on_confirm=self._close_reconstruction,
                on_save=self._save_reconstruction,
                ok_label=LBL_BUTTON_GLOBAL_CLOSE,
            )
        else:
            self._close_reconstruction()

    def _close_reconstruction(self) -> None:
        self.reconstruction_manager.close_reconstruction()

    def _on_reconstruction_closed(self) -> None:
        self._reconstructions_tab.close_reconstruction()
        self.application_config_manager.set_current_reconstruction(None)
        self._unsaved_reconstruction_changes = False
        self._update_menu()
        self._update_viewport_title("")

    def _set_current_tab(self, tab_tag: str) -> None:
        dpg_set_value(TAG_TABS, tab_tag)
        self.application_config_manager.set_current_tab(tab_tag)

    def _get_current_tab(self) -> str:
        current_tab = dpg.get_value(TAG_TABS)
        alias: str = dpg.get_item_alias(current_tab)
        return alias

    def _persist_application_state(self) -> None:
        self.application_config_manager.set_current_audio_device(self.audio_device_manager)
        self._viewport_manager.save_window_state()
        self.application_config_manager.set_current_tab(self._get_current_tab())
        self.application_config_manager.save_config()

    def _play_from_start(self) -> None:
        current_tab_tag = self._get_current_tab()
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            self._reconstructions_tab.player_panel.play()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            self._instructions_tab.player_panel.play()

        self._update_menu()

    def _play(self) -> None:
        current_tab_tag = self._get_current_tab()
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            self._reconstructions_tab.player_panel.pause_or_resume()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            self._instructions_tab.player_panel.pause_or_resume()

        self._update_menu()

    def _stop(self) -> None:
        current_tab_tag = self._get_current_tab()
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            self._reconstructions_tab.player_panel.stop()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            self._instructions_tab.player_panel.stop()

        self._update_menu()

    def _get_play_label(self) -> str:
        current_tab_tag = self._get_current_tab()
        playing = False
        loaded = False
        paused = False
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            playing = self._reconstructions_tab.player_panel.is_playing()
            paused = self._reconstructions_tab.player_panel.is_paused()
            loaded = self._reconstructions_tab.player_panel.is_loaded()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            playing = self._instructions_tab.player_panel.is_playing()
            paused = self._instructions_tab.player_panel.is_paused()
            loaded = self._instructions_tab.player_panel.is_loaded()

        is_playing = loaded and playing
        if is_playing:
            return LBL_MENU_ITEM_PLAYBACK_RESUME if paused else LBL_MENU_ITEM_PLAYBACK_PAUSE

        return LBL_MENU_ITEM_PLAYBACK_PLAY

    def _is_play_or_pause_enabled(self) -> bool:
        current_tab_tag = self._get_current_tab()
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            return self._reconstructions_tab.player_panel.is_loaded()

        if current_tab_tag == TAG_TAB_INSTRUCTIONS:
            return self._instructions_tab.player_panel.is_loaded()

        return False

    def _is_stop_enabled(self) -> bool:
        current_tab_tag = self._get_current_tab()
        loaded = False
        playing = False
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            loaded = self._reconstructions_tab.player_panel.is_loaded()
            playing = self._reconstructions_tab.player_panel.is_playing()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            loaded = self._instructions_tab.player_panel.is_loaded()
            playing = self._instructions_tab.player_panel.is_playing()

        return loaded and playing

    def _show_confirmation_dialog(self, message: str, ok_label: str = LBL_BUTTON_GLOBAL_OK) -> None:
        show_confirmation_dialog(
            tag=TAG_DIALOG_GLOBAL_EXIT_CONFIRMATION,
            title=TTL_DIALOG_EXIT_CONFIRMATION,
            message=message,
            on_confirm=self._exit_application,
            ok_label=ok_label,
        )

    def _show_save_confirmation_dialog(
        self,
        title: str,
        message: str,
        on_save: Callback,
        on_confirm: Callback,
        ok_label: str = LBL_BUTTON_GLOBAL_OK,
    ) -> None:
        show_save_confirmation_dialog(
            tag=TAG_DIALOG_GLOBAL_EXIT_CONFIRMATION,
            title=title,
            message=message,
            on_save=on_save,
            on_confirm=on_confirm,
            ok_label=ok_label,
        )

    def _on_close(self) -> None:
        if self._is_reconstruction_unsaved():
            self._show_save_confirmation_dialog(
                TTL_DIALOG_EXIT_CONFIRMATION,
                MSG_GLOBAL_EXIT_UNSAVED_RECONSTRUCTION,
                on_save=self._save_reconstruction,
                on_confirm=self._exit_application,
                ok_label=LBL_BUTTON_GLOBAL_EXIT,
            )
        elif self._is_converter_running():
            self._show_confirmation_dialog(
                MSG_GLOBAL_EXIT_CONVERSION_IN_PROGRESS,
                ok_label=LBL_BUTTON_GLOBAL_EXIT,
            )
        elif self._is_library_generating():
            self._show_confirmation_dialog(
                MSG_GLOBAL_EXIT_LIBRARY_GENERATION_IN_PROGRESS,
                ok_label=LBL_BUTTON_GLOBAL_EXIT,
            )
        else:
            self._exit_application()

    def _is_converter_running(self) -> bool:
        return self._main_tab.is_converter_running()

    def _is_library_generating(self) -> bool:
        return self._instructions_tab.is_library_generating()

    def _is_reconstruction_unsaved(self) -> bool:
        return self._unsaved_reconstruction_changes

    def _exit_application(self) -> None:
        CallbackQueue.stop()
        self.audio_device_manager.stop()
        self._main_tab.converter_logic.cleanup()

        dpg.stop_dearpygui()

    def _toggle_fullscreen(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self._viewport_manager.toggle_fullscreen()

    def _update_fullscreen_menu_item(self) -> None:
        fullscreen = self.application_config_manager.fullscreen
        dpg_set_value(TAG_MENU_ITEM_VIEW_FULLSCREEN, fullscreen)

    def _toggle_autoplay(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self.application_config_manager.toggle_autoplay()
        self._update_playback_menu_items()

    def _update_reconstruction_menu_items(self) -> None:
        reconstruction_loaded = self._is_reconstruction_loaded()
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV, enabled=reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS, enabled=reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_CLOSE, enabled=reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_SAVE, enabled=reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_SAVE_AS, enabled=reconstruction_loaded)

    def _update_playback_menu_items(self) -> None:
        dpg_configure_item(TAG_MENU_ITEM_PLAYBACK_PLAY_FROM_START, enabled=self._is_play_or_pause_enabled())
        dpg_configure_item(
            TAG_MENU_ITEM_PLAYBACK_PLAY,
            label=self._get_play_label(),
            enabled=self._is_play_or_pause_enabled(),
        )
        dpg_configure_item(TAG_MENU_ITEM_PLAYBACK_STOP, enabled=self._is_stop_enabled())
        dpg_set_value(TAG_MENU_ITEM_PLAYBACK_AUTOPLAY, self.application_config_manager.autoplay)

    def _toggle_advanced_settings(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self._main_tab.toggle_advanced_settings()
        self._update_advanced_settings_menu_item()

    def _update_advanced_settings_menu_item(self) -> None:
        advanced_settings = self.application_config_manager.advanced_settings
        self._main_tab.sync_advanced_settings_visibility()
        dpg_set_value(TAG_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS, advanced_settings)

    def _update_fps(self, delta_time: float) -> None:
        fps = self.fps_timer.update(delta_time)
        dpg_configure_item(TAG_MENU_TEXT_FPS, label=TPL_MENU_TEXT_FPS.format(fps=fps))

    def _update_status(self) -> None:
        delta_time = dpg.get_delta_time()
        self._update_fps(delta_time)
        self._update_status_bar(delta_time)

    def _update_status_bar(self, delta_time: float) -> None:
        self.status_bar.update(delta_time=delta_time)

    def frame(self) -> None:
        dpg.render_dearpygui_frame()

    def _post_frame(self) -> None:
        CallbackQueue.notify_frame()
        CallbackQueue.add(self._update_status, priority=VAL_PRIORITY_UPDATE_STATUS)

    def run(self) -> None:
        try:
            while dpg.is_dearpygui_running():
                self.frame()
                self._post_frame()
        except KeyboardInterrupt:
            return
        finally:
            self._main_tab.converter_logic.cleanup()
            self.config_manager.save_config()
            self._persist_application_state()
            self.audio_device_manager.terminate()
            dpg.destroy_context()
