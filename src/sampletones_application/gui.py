import sys
import tkinter
from pathlib import Path
from typing import Any, List, Optional, Tuple

import dearpygui.dearpygui as dpg
from screeninfo import Monitor, get_monitors

from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.paths import EXT_FILE_JSON, EXT_FILE_RECONSTRUCTION, EXT_FILES_AUDIO
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.sequencer import Sequencer
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionError,
    InvalidReconstructionValuesError,
    LibraryDisplayError,
    LoadReconstructionError,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback, VoidCallback

from .config.application.manager import ApplicationConfigManager
from .config.manager import ConfigManager
from .constants.general import (
    DIM_DIALOG_HEIGHT_FILE,
    DIM_DIALOG_WIDTH_FILE,
    DIM_PANEL_HEIGHT_LEFT,
    DIM_PANEL_HEIGHT_RIGHT,
    DIM_PANEL_WIDTH_INSTRUCTIONS_DETAILS,
    DIM_PANEL_WIDTH_LEFT,
    DIM_PANEL_WIDTH_RECONSTRUCTIONS_DETAILS,
    DIM_STATUS_HEIGHT,
    DIM_WINDOW_HEIGHT,
    DIM_WINDOW_WIDTH,
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
    LBL_TAB_INSTRUCTIONS,
    LBL_TAB_MAIN,
    LBL_TAB_RECONSTRUCTIONS,
    LBL_TAB_SEQUENCER,
    MSG_ALL_AUDIO_FORMATS,
    MSG_AUDIO_PLAYBACK_ERROR,
    MSG_CONFIGURATION_LOADED_SUCCESSFULLY,
    MSG_CONFIGURATION_SAVED_SUCCESSFULLY,
    MSG_GLOBAL_CLOSE_UNSAVED_RECONSTRUCTION,
    MSG_GLOBAL_CONFIG_SAVE_FAILED,
    MSG_GLOBAL_EXIT_CONVERSION_IN_PROGRESS,
    MSG_GLOBAL_EXIT_LIBRARY_GENERATION_IN_PROGRESS,
    MSG_GLOBAL_EXIT_UNSAVED_RECONSTRUCTION,
    MSG_GLOBAL_INVALID_METADATA_ERROR,
    MSG_GLOBAL_LOAD_UNSAVED_RECONSTRUCTION,
    MSG_GLOBAL_RECONSTRUCTION_SAVE_FAILED,
    MSG_GLOBAL_RECONSTRUCTION_SAVED_SUCCESSFULLY,
    SUF_PANEL_CENTER,
    SUF_PANEL_LEFT,
    SUF_PANEL_RIGHT,
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
    TAG_TAB_SEQUENCER,
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
from .constants.instructions import MSG_LIBRARY_DISPLAY_ERROR
from .constants.main import (
    DIM_PANEL_HEIGHT_MAIN_EXPLORER,
    DIM_PANEL_WIDTH_MAIN_EXPLORER,
    MSG_MAIN_CONVERTER_ERROR,
    MSG_MAIN_CONVERTER_NO_FILES_TO_PROCESS,
    TTL_DIALOG_MAIN_CONVERTER_PROGRESS,
)
from .constants.reconstructions import (
    MSG_RECONSTRUCTIONS_BROWSER_DESERIALIZATION_ERROR,
    MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR,
    MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_FILE,
    MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_VALUES,
    MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_AUDIO_FILE_NOT_FOUND,
    MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_FILE_NOT_FOUND,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_SUCCESS,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_SUCCESS,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_SUCCESS,
    MSG_RECONSTRUCTIONS_RECONSTRUCTION_LOCATE_AUDIO_FAILED,
    TAG_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
    TPL_RECONSTRUCTIONS_BROWSER_INCOMPATIBLE_RECONSTRUCTION_FILE,
    TTL_DIALOG_EXPORT_WAV,
    TTL_DIALOG_LOAD_RECONSTRUCTION,
    TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
    TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
)
from .constants.sequencer import DIM_PANEL_WIDTH_SEQUENCER_INSTRUMENTS
from .elements.fonts.registry import FontRegistry
from .elements.status import GUIStatusBar
from .instruction.data import InstructionPanelData
from .library.manager import InstructionsLibraryManager
from .panels.instruction.details.logic import InstructionDetailsPanelLogic
from .panels.instruction.details.panel import GUIInstructionDetailsPanel
from .panels.instruction.instruction.logic import InstructionPanelLogic
from .panels.instruction.instruction.panel import GUIInstructionPanel
from .panels.instruction.library.logic import LibraryLogic
from .panels.instruction.library.panel import GUIInstructionsLibraryPanel
from .panels.main.advanced.panel import GUIAdvancedSettingsPanel
from .panels.main.advanced.viewmodel import AdvancedSettingsPanelViewModel
from .panels.main.config.panel import GUIConfigPanel
from .panels.main.config.viewmodel import ConfigPanelViewModel
from .panels.main.converter.logic import ConverterLogic
from .panels.main.converter.panel import GUIConverterPanel
from .panels.main.converter.success_dialog import ConverterSuccessDialog
from .panels.main.explorer.logic import ExplorerLogic
from .panels.main.explorer.panel import GUIExplorerPanel
from .panels.main.main import GUIMainPanel
from .panels.main.reconstructor.panel import GUIReconstructorPanel
from .panels.main.reconstructor.viewmodel import ReconstructorPanelViewModel
from .panels.reconstruction.browser.logic import BrowserLogic
from .panels.reconstruction.browser.panel import GUIBrowserPanel
from .panels.reconstruction.details.logic import ReconstructionDetailsLogic
from .panels.reconstruction.details.panel import GUIReconstructionDetailsPanel
from .panels.reconstruction.reconstruction.logic import ReconstructionPanelLogic
from .panels.reconstruction.reconstruction.panel import GUIReconstructionPanel
from .panels.sequencer.browser.logic import SequencerBrowserLogic
from .panels.sequencer.browser.panel import GUISequencerBrowserPanel
from .panels.sequencer.grid import GUISequencerGridPanel
from .panels.sequencer.samples import GUISequencerSamplesPanel
from .panels.settings import GUIAudioSettingsWindow
from .reconstruction.browser import BrowserManager
from .reconstruction.manager import ReconstructionManager
from .reconstruction.regenerator import Regenerator
from .resources.items import IconResource
from .resources.resources import get_icon_path
from .themes.default import DefaultTheme
from .themes.fps import FPSTimerTheme
from .utils.callbacks.queue import CallbackQueue
from .utils.dialogs import (
    show_confirmation_dialog,
    show_error_dialog,
    show_file_not_found_dialog,
    show_info_dialog,
    show_message_with_path_dialog,
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


class GUI:
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

        self.explorer_logic: ExplorerLogic = ExplorerLogic(self.config_manager)
        self.explorer_panel: GUIExplorerPanel = GUIExplorerPanel(
            self.explorer_logic,
            self.application_config_manager,
            self.audio_device_manager,
            self.shortcut_manager,
        )
        self.library_logic: LibraryLogic = LibraryLogic(self.config_manager, self.library_manager)
        self.library_panel: GUIInstructionsLibraryPanel = GUIInstructionsLibraryPanel(
            self.library_logic,
            self.application_config_manager,
            self.audio_device_manager,
            self.shortcut_manager,
        )
        self.instruction_panel_logic: InstructionPanelLogic = InstructionPanelLogic()
        self.instruction_panel: GUIInstructionPanel = GUIInstructionPanel(self.audio_device_manager)
        self.instruction_details_logic: InstructionDetailsPanelLogic = InstructionDetailsPanelLogic(
            self.library_manager
        )
        self.instruction_details_panel: GUIInstructionDetailsPanel = GUIInstructionDetailsPanel()
        self.browser_logic: BrowserLogic = BrowserLogic(self.config_manager, self.browser_manager)
        self.browser_panel: GUIBrowserPanel = GUIBrowserPanel(
            self.browser_logic,
            self.application_config_manager,
            self.audio_device_manager,
            self.shortcut_manager,
        )
        self.reconstruction_panel: GUIReconstructionPanel = GUIReconstructionPanel(
            self.audio_device_manager,
        )
        self.reconstruction_panel_logic: ReconstructionPanelLogic = ReconstructionPanelLogic(
            self.application_config_manager,
            self.reconstruction_manager,
        )
        self.reconstruction_details_panel: GUIReconstructionDetailsPanel = GUIReconstructionDetailsPanel(
            self.shortcut_manager,
        )
        self.reconstruction_details_logic: ReconstructionDetailsLogic = ReconstructionDetailsLogic(
            self.reconstruction_manager,
        )
        self.sequencer_browser_logic: SequencerBrowserLogic = SequencerBrowserLogic(
            self.config_manager, self.browser_manager
        )
        self.sequencer_browser_panel: GUISequencerBrowserPanel = GUISequencerBrowserPanel(
            self.sequencer_browser_logic,
            self.application_config_manager,
            self.audio_device_manager,
            self.shortcut_manager,
        )
        self.sequencer_grid_panel: GUISequencerGridPanel = GUISequencerGridPanel(
            self.config_manager,
            self.application_config_manager,
            self.audio_device_manager,
        )
        self.sequencer_instruments_panel: GUISequencerSamplesPanel = GUISequencerSamplesPanel()
        _config = self.config_manager.config
        self.config_panel: GUIConfigPanel = GUIConfigPanel(
            ConfigPanelViewModel(
                normalize=_config.general.normalize,
                quantize=_config.general.quantize,
                sample_rate=_config.library.sample_rate,
                change_rate=_config.library.change_rate,
                transformation_gamma=_config.library.transformation_gamma,
            )
        )
        self.reconstructor_panel: GUIReconstructorPanel = GUIReconstructorPanel(
            ReconstructorPanelViewModel(
                generators=frozenset(_config.generation.generators),
                mixer=_config.generation.mixer,
            )
        )
        self.advanced_settings_panel: GUIAdvancedSettingsPanel = GUIAdvancedSettingsPanel(
            AdvancedSettingsPanelViewModel(
                max_workers=_config.general.max_workers,
                library_directory=self.config_manager.get_library_directory(),
                output_directory=self.config_manager.get_output_directory(),
            )
        )
        self.converter_logic: ConverterLogic = ConverterLogic(self.config_manager)
        self.converter_panel: GUIConverterPanel = GUIConverterPanel()
        self.converter_success_dialog: ConverterSuccessDialog = ConverterSuccessDialog()
        self.main_panel: GUIMainPanel = GUIMainPanel(
            self.config_panel,
            self.reconstructor_panel,
            self.advanced_settings_panel,
            self.converter_panel,
        )
        self.audio_settings_window: GUIAudioSettingsWindow = GUIAudioSettingsWindow(self.audio_device_manager)

        self.status_bar = GUIStatusBar()
        self.theme = DefaultTheme()
        self.fps_theme = FPSTimerTheme()

        self._unsaved_reconstruction_changes: bool = False
        self._reconstruction_name: Optional[str] = None

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
        self._set_viewport()
        self._setup_dearpygui()
        self._set_callbacks()
        self._setup_handlers()
        self._create_main_window()
        self.converter_logic.emit_initial_view()
        self.config_manager.update_gui()
        self._update_menu()
        self._restore_current_items()
        self._start_callback_worker()
        dpg.set_exit_callback(self._on_close)

    def _start_callback_worker(self) -> None:
        CallbackQueue.start()

    def _on_exit(self) -> None:
        dpg.start_dearpygui()

    def _setup_dearpygui(self) -> None:
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.render_dearpygui_frame()

    def _update_viewport_title(self, name: Optional[str] = None) -> None:
        if name is None:
            name = self._reconstruction_name

        self._reconstruction_name = name
        if not self._reconstruction_name:
            base_name = TTL_WINDOW_MAIN
        else:
            base_name = f"{TTL_WINDOW_MAIN} - {name}"
            if self._unsaved_reconstruction_changes and name:
                base_name += "*"

        dpg.set_viewport_title(base_name)

    def _set_fonts(self) -> None:
        FontRegistry.register_fonts()

    def _set_default_theme(self) -> None:
        self.theme.bind()

    def _set_viewport(self) -> None:
        if sys.platform.startswith("win"):
            icon_filename = IconResource.WIN
        else:
            icon_filename = IconResource.UNIX

        icon_file_path = get_icon_path(icon_filename)

        dpg.create_viewport(
            title=TTL_WINDOW_MAIN,
            width=DIM_WINDOW_WIDTH,
            height=DIM_WINDOW_HEIGHT,
            small_icon=str(icon_file_path),
            large_icon=str(icon_file_path),
            x_pos=self.application_config_manager.window_x,
            y_pos=self.application_config_manager.window_y,
            decorated=not self.application_config_manager.fullscreen,
            disable_close=True,
        )

        if self.application_config_manager.fullscreen:
            self._enable_fullscreen()
        else:
            self._disable_fullscreen()

        color = self.theme.get_color(dpg.mvAll, dpg.mvThemeCol_WindowBg)
        assert color is not None, "Background color is not defined in the main theme"
        dpg.set_viewport_clear_color(list(color))

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
        self.config_manager.add_config_change_callback(self.library_logic.update_status)
        self.config_manager.add_config_change_callback(self._update_menu)
        self.config_manager.add_config_change_callback(self._update_config_panel_view)
        self.config_manager.add_config_change_callback(self._update_reconstructor_panel_view)
        self.config_manager.add_config_change_callback(self._update_advanced_settings_panel_view)

        self.config_panel.on_audio_settings_changed = self.config_manager.apply_audio_settings
        self.config_panel.on_library_settings_changed = self.config_manager.apply_library_settings
        self.reconstructor_panel.on_generation_settings_changed = self.config_manager.apply_generation_settings
        self.advanced_settings_panel.on_advanced_settings_changed = self.config_manager.apply_advanced_settings
        self.advanced_settings_panel.on_library_path_memorized = self.application_config_manager.set_library_path

        self.audio_device_manager.set_callbacks(
            on_playback_error=self._on_playback_error,
        )
        self.reconstruction_manager.set_callbacks(
            on_reconstruction_loaded=self._on_reconstruction_loaded,
            on_reconstruction_closed=self._on_reconstruction_closed,
        )
        self.regenerator.set_callbacks(
            on_regeneration_finished=self._on_reconstruction_updated,
        )

        self.explorer_panel.set_callbacks(
            on_wave_file_clicked=self._assign_file_to_converter,
            on_directory_clicked=self._assign_directory_to_converter,
            on_reconstruct_file=self._reconstruct_file,
            on_reconstruct_directory=self._reconstruct_directory,
            on_load_reconstruction=self._load_reconstruction_with_confirmation,
            on_load_library=self._load_library,
            on_set_as_library_directory=self.advanced_settings_panel.change_library_directory,
            on_set_as_output_directory=self.advanced_settings_panel.change_output_directory,
            is_converter_running=self._is_generation_in_progress,
        )
        self.library_logic.set_callbacks(
            on_apply_library_config=self.config_manager.apply_library_config,
            on_instruction_loaded=self._on_instruction_loaded,
        )
        self.browser_logic.set_callbacks(
            load_reconstruction_with_confirmation=self._load_reconstruction_with_confirmation,
            on_reconstruction_loaded=self._on_reconstruction_loaded,
            on_reconstruct_file=self._reconstruct_file_dialog,
            on_reconstruct_directory=self._reconstruct_directory_dialog,
        )
        self.instruction_panel.set_callbacks(
            on_clear_instruction_details=self.instruction_details_logic.clear_display,
            on_change_audio_state=self._update_menu,
        )
        self.instruction_panel.on_instruction_config_changed = self.instruction_panel_logic.update_config
        self.instruction_details_logic.on_view_changed = self.instruction_details_panel.update_view
        self.instruction_details_logic.on_instruction_changed = self.instruction_panel.display_instruction
        self.instruction_details_panel.on_instruction_parameter_changed = (
            self.instruction_details_logic.handle_instruction_parameter_changed
        )
        self.reconstruction_panel.on_change_audio_state = self._update_menu
        self.reconstruction_panel.on_audio_source_changed = self.reconstruction_panel_logic.set_audio_source
        self.reconstruction_panel.on_generators_changed = self.reconstruction_panel_logic.set_selected_generators
        self.reconstruction_panel.on_export_wav_requested = self._export_reconstruction_wav_dialog
        self.reconstruction_panel.on_export_instrument_confirmed = (
            self.reconstruction_panel_logic.handle_export_instrument_confirmed
        )
        self.reconstruction_panel.on_export_instruments_confirmed = (
            self.reconstruction_panel_logic.handle_export_instruments_confirmed
        )
        self.reconstruction_panel.on_export_wav_confirmed = self.reconstruction_panel_logic.handle_export_wav_confirmed
        self.reconstruction_panel.on_locate_original_audio_requested = (
            self.reconstruction_panel_logic.handle_locate_original_audio
        )

        self.reconstruction_panel_logic.on_view_changed = self.reconstruction_panel.update_view
        self.reconstruction_panel_logic.on_audio_data_changed = self.reconstruction_panel.update_audio_data
        self.reconstruction_panel_logic.on_waveform_load_changed = self.reconstruction_panel.load_waveform_data
        self.reconstruction_panel_logic.on_waveform_update_changed = self.reconstruction_panel.update_waveform_data
        self.reconstruction_panel_logic.on_waveform_cleared = self.reconstruction_panel.clear_waveform
        self.reconstruction_panel_logic.on_open_export_instrument_dialog = (
            self.reconstruction_panel.open_export_instrument_dialog
        )
        self.reconstruction_panel_logic.on_open_export_instruments_dialog = (
            self.reconstruction_panel.open_export_instruments_dialog
        )
        self.reconstruction_panel_logic.on_open_export_wav_dialog = self.reconstruction_panel.open_export_wav_dialog
        self.reconstruction_panel_logic.on_export_instrument_success = lambda filepath: show_message_with_path_dialog(
            TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
            MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_SUCCESS,
            filepath,
        )
        self.reconstruction_panel_logic.on_export_instrument_error = lambda exception: show_error_dialog(
            exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTI_FAILED
        )
        self.reconstruction_panel_logic.on_export_instruments_success = lambda filepath: show_message_with_path_dialog(
            TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_STATUS,
            MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_SUCCESS,
            filepath,
        )
        self.reconstruction_panel_logic.on_export_instruments_error = lambda exception: show_error_dialog(
            exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_FTIS_FAILED
        )
        self.reconstruction_panel_logic.on_export_wav_success = lambda filepath: show_message_with_path_dialog(
            TTL_DIALOG_EXPORT_WAV,
            MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_SUCCESS,
            filepath,
        )
        self.reconstruction_panel_logic.on_export_wav_error = lambda exception: show_error_dialog(
            exception, MSG_RECONSTRUCTIONS_RECONSTRUCTION_EXPORT_WAV_FAILED
        )
        self.reconstruction_panel_logic.on_locate_audio_missing = lambda: show_info_dialog(
            TAG_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
            MSG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
            TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_AUDIO_MISSING,
        )
        self.reconstruction_panel_logic.on_locate_audio_not_found = lambda path: show_file_not_found_dialog(
            path, MSG_RECONSTRUCTIONS_RECONSTRUCTION_LOCATE_AUDIO_FAILED
        )

        self.reconstruction_details_logic.on_view_changed = self.reconstruction_details_panel.update_view
        self.reconstruction_details_logic.on_feature_data_changed = (
            self.reconstruction_details_panel.update_feature_data
        )
        self.reconstruction_details_logic.on_pitch_changed = self.reconstruction_details_panel.update_pitch
        self.reconstruction_details_logic.on_reconstruction_instrument_updated = self.regenerator.regenerate

        self.reconstruction_details_panel.on_instrument_export = (
            self.reconstruction_panel_logic.request_export_instrument_dialog
        )
        self.reconstruction_details_panel.on_instruments_export = (
            self.reconstruction_panel_logic.request_export_instruments_dialog
        )
        self.reconstruction_details_panel.on_reconstruction_instrument_hovered = self.reconstruction_panel.set_overlay
        self.reconstruction_details_panel.on_pitch_input = self.reconstruction_details_logic.handle_pitch_input
        self.reconstruction_details_panel.on_pitch_step = self.reconstruction_details_logic.handle_pitch_step
        self.reconstruction_details_panel.on_hold_tick = self.reconstruction_details_logic.handle_hold_tick
        self.reconstruction_details_panel.on_hold_ended = self.reconstruction_details_logic.handle_hold_ended
        self.reconstruction_details_panel.on_bar_data_changed = (
            self.reconstruction_details_logic.handle_bar_point_clicked
        )
        self.reconstruction_details_panel.on_raw_data_changed = (
            self.reconstruction_details_logic.handle_raw_data_changed
        )
        self.converter_logic.on_view_changed = self.converter_panel.update_view
        self.converter_logic.on_success = self.converter_success_dialog.show
        self.converter_logic.on_error = lambda error: show_error_dialog(error, MSG_MAIN_CONVERTER_ERROR)
        self.converter_logic.on_no_files_to_process = lambda: show_info_dialog(
            self.converter_panel.tag, MSG_MAIN_CONVERTER_NO_FILES_TO_PROCESS, TTL_DIALOG_MAIN_CONVERTER_PROGRESS
        )
        self.converter_logic.on_load_file = self._on_converted_reconstruction_loaded
        self.converter_logic.on_load_directory = self.browser_panel.refresh
        self.converter_logic.on_cancelled = self.browser_panel.refresh
        self.converter_logic.generate_library = self._generate_library_if_not_loaded
        self.converter_logic.is_library_loaded = self.library_manager.is_library_loaded
        self.converter_panel.on_convert_requested = self.converter_logic.start_conversion
        self.converter_panel.on_cancel_requested = self.converter_logic.cancel
        self.converter_panel.on_close_requested = self.converter_logic.close
        self.converter_panel.on_load_requested = self.converter_logic.handle_load_request

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
                self._create_main_tab()
                self._create_reconstructions_tab()
                self._create_sequencer_tab()
                self._create_instructions_tab()

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

    def _create_main_tab(self) -> None:
        with dpg.tab(
            label=LBL_TAB_MAIN,
            tag=TAG_TAB_MAIN,
            parent=TAG_TABS,
        ):
            with dpg.table(
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{TAG_TAB_MAIN}{SUF_PANEL_LEFT}",
                        width=DIM_PANEL_WIDTH_MAIN_EXPLORER,
                        height=DIM_PANEL_HEIGHT_MAIN_EXPLORER,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        self._create_main_left_panel()

                    with dpg.child_window(
                        tag=f"{TAG_TAB_MAIN}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        self._create_main_panel()

    @staticmethod
    def _create_layout(
        label: str,
        tab_tag: str,
        parent: str,
        left_content_builder: VoidCallback,
        center_content_builder: VoidCallback,
        right_content_builder: VoidCallback,
        right_panel_height: int,
        right_panel_width: int,
        left_panel_width: int = DIM_PANEL_WIDTH_LEFT,
        left_panel_height: int = DIM_PANEL_HEIGHT_LEFT,
    ) -> None:
        with dpg.tab(
            tag=tab_tag,
            parent=parent,
            label=label,
        ):
            with dpg.table(
                parent=tab_tag,
                header_row=False,
                resizable=False,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(width_fixed=True)
                dpg.add_table_column()
                dpg.add_table_column(width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(
                        tag=f"{tab_tag}{SUF_PANEL_LEFT}",
                        width=left_panel_width,
                        height=left_panel_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        left_content_builder()

                    with dpg.child_window(
                        tag=f"{tab_tag}{SUF_PANEL_CENTER}",
                        no_scroll_with_mouse=True,
                    ):
                        center_content_builder()

                    with dpg.child_window(
                        tag=f"{tab_tag}{SUF_PANEL_RIGHT}",
                        width=right_panel_width,
                        height=right_panel_height,
                        no_scrollbar=True,
                        no_scroll_with_mouse=True,
                    ):
                        right_content_builder()

    def _create_reconstructions_tab(self) -> None:
        self._create_layout(
            label=LBL_TAB_RECONSTRUCTIONS,
            tab_tag=TAG_TAB_RECONSTRUCTIONS,
            parent=TAG_TABS,
            left_content_builder=self._create_reconstructions_left_panel,
            center_content_builder=self.reconstruction_panel.create_panel,
            right_content_builder=self.reconstruction_details_panel.create_panel,
            right_panel_height=DIM_PANEL_HEIGHT_RIGHT,
            right_panel_width=DIM_PANEL_WIDTH_RECONSTRUCTIONS_DETAILS,
        )

    def _create_instructions_tab(self) -> None:
        self._create_layout(
            label=LBL_TAB_INSTRUCTIONS,
            tab_tag=TAG_TAB_INSTRUCTIONS,
            parent=TAG_TABS,
            left_content_builder=self._create_instructions_left_panel,
            center_content_builder=self.instruction_panel.create_panel,
            right_content_builder=self.instruction_details_panel.create_panel,
            right_panel_height=DIM_PANEL_HEIGHT_RIGHT,
            right_panel_width=DIM_PANEL_WIDTH_INSTRUCTIONS_DETAILS,
        )

    def _create_sequencer_tab(self) -> None:
        self._create_layout(
            label=LBL_TAB_SEQUENCER,
            tab_tag=TAG_TAB_SEQUENCER,
            parent=TAG_TABS,
            left_content_builder=self._create_sequencer_left_panel,
            center_content_builder=self.sequencer_grid_panel.create_panel,
            right_content_builder=self.sequencer_instruments_panel.create_panel,
            right_panel_height=DIM_PANEL_HEIGHT_RIGHT,
            right_panel_width=DIM_PANEL_WIDTH_SEQUENCER_INSTRUMENTS,
        )

    def _create_instructions_left_panel(self) -> None:
        self.library_panel.create_panel()

    def _create_reconstructions_left_panel(self) -> None:
        self.browser_panel.create_panel()

    def _create_sequencer_left_panel(self) -> None:
        self.sequencer_browser_panel.create_panel()

    def _create_main_left_panel(self) -> None:
        self.explorer_panel.create_panel()

    def _create_main_panel(self) -> None:
        self.main_panel.create_panel()

    def _update_config_panel_view(self) -> None:
        config = self.config_manager.config
        self.config_panel.update_view(
            ConfigPanelViewModel(
                normalize=config.general.normalize,
                quantize=config.general.quantize,
                sample_rate=config.library.sample_rate,
                change_rate=config.library.change_rate,
                transformation_gamma=config.library.transformation_gamma,
            )
        )

    def _update_reconstructor_panel_view(self) -> None:
        config = self.config_manager.config
        self.reconstructor_panel.update_view(
            ReconstructorPanelViewModel(
                generators=frozenset(config.generation.generators),
                mixer=config.generation.mixer,
            )
        )

    def _update_advanced_settings_panel_view(self) -> None:
        self.advanced_settings_panel.update_view(
            AdvancedSettingsPanelViewModel(
                max_workers=self.config_manager.config.general.max_workers,
                library_directory=self.config_manager.get_library_directory(),
                output_directory=self.config_manager.get_output_directory(),
            )
        )

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
        if self.converter_logic.is_running():
            logger.warning("A conversion is already in progress; cannot start a new one")
            return

        self._generate_library_if_not_loaded()
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
        if self.converter_logic.is_running():
            logger.warning("A conversion is already in progress; cannot start a new one")
            return

        self._generate_library_if_not_loaded()
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
                self._load_reconstruction(filepath)

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
        return self.converter_logic.is_running() or self.library_panel.is_library_generating()

    def _on_instruction_loaded(self, instruction_data: InstructionPanelData) -> None:
        try:
            self.instruction_panel.display_instruction(instruction_data)
            self.instruction_details_logic.display_instruction(instruction_data)
        except LibraryDisplayError as exception:
            show_error_dialog(exception, MSG_LIBRARY_DISPLAY_ERROR)

        self._update_menu()

    def _export_reconstruction_wav_dialog(self) -> None:
        if self._check_if_reconstruction_loaded():
            self.reconstruction_panel_logic.request_export_wav_dialog()

    def _export_reconstruction_ftis_dialog(self) -> None:
        if self._check_if_reconstruction_loaded():
            self.reconstruction_panel_logic.request_export_instruments_dialog()

    def _check_if_reconstruction_loaded(self) -> bool:
        if not self._is_reconstruction_loaded():
            logger.warning("No reconstruction loaded; cannot proceed")
            show_reconstruction_not_loaded_dialog()
            return False

        return True

    @staticmethod
    def _get_monitors() -> List[Monitor]:
        return get_monitors()

    def _monitor_for_position(self, x: float, y: float) -> Optional[Monitor]:
        monitors = self._get_monitors()
        position_x = float(x)
        position_y = float(y)

        for monitor in monitors:
            if all(
                (
                    monitor.x <= position_x < (monitor.x + monitor.width),
                    monitor.y <= position_y < (monitor.y + monitor.height),
                )
            ):
                return monitor

        return monitors[0] if monitors else None

    def _is_reconstruction_loaded(self) -> bool:
        return self.reconstruction_manager.is_reconstruction_loaded()

    def _is_library_loaded(self, library_key: Optional[InstructionLibraryKey] = None) -> bool:
        return self.library_manager.is_library_loaded(library_key)

    def _does_library_exist(self, library_key: Optional[InstructionLibraryKey] = None) -> bool:
        return self.library_manager.does_library_exist(library_key)

    def _generate_library_if_not_loaded(self) -> None:
        if not self._does_library_exist():
            self.library_panel.generate_library()

        self.library_panel.load_current_library()

    def _assign_file_to_converter(self, filepath: Path) -> None:
        if not self._is_generation_in_progress():
            self.converter_logic.set_input_path(filepath, convert=False)

    def _assign_directory_to_converter(self, directory_path: Path) -> None:
        if not self._is_generation_in_progress():
            self.converter_logic.set_input_path(directory_path, convert=False)

    def _reconstruct_file(self, filepath: Path) -> None:
        self.converter_logic.set_input_path(filepath, convert=True)
        self.application_config_manager.set_reconstruction_path(filepath.parent)
        self._set_current_tab(TAG_TAB_MAIN)
        self._update_menu()

    def _load_library(self, filepath: Path) -> None:
        self.instruction_panel.close_instruction()
        self.library_panel.load_library_file(filepath)

        self.config_manager.update_gui()
        self._set_current_tab(TAG_TAB_INSTRUCTIONS)
        self._update_menu()

    @file_dialog_handler
    def _handle_reconstruct_file(self, filepath: Path) -> None:
        self._reconstruct_file(filepath)

    def _reconstruct_directory(self, directory_path: Path) -> None:
        self.converter_logic.set_input_path(directory_path, convert=True)
        self.application_config_manager.set_reconstruction_path(directory_path)
        self._set_current_tab(TAG_TAB_MAIN)
        self._update_menu()

    @file_dialog_handler
    def _handle_reconstruct_directory(self, directory_path: Path) -> None:
        self._reconstruct_directory(directory_path)

    def _load_reconstruction(self, filepath: Path) -> None:
        self.browser_panel.lock()
        try:
            self.reconstruction_manager.load_reconstruction(filepath)
            logger.info(f"Loaded reconstruction: {logger.format_path(filepath)}")
        except FileNotFoundError as exception:
            logger.error_with_traceback(exception, f"Failed to load reconstruction data from {filepath}")
            show_file_not_found_dialog(filepath, MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_FILE_NOT_FOUND)
        except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"Error while loading reconstruction data from {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR)
        except InvalidMetadataError as exception:
            logger.error_with_traceback(exception, f"Invalid metadata in the reconstruction file {filepath}")
            show_error_dialog(exception, MSG_GLOBAL_INVALID_METADATA_ERROR)
        except InvalidReconstructionValuesError as exception:
            logger.error_with_traceback(exception, f"Reconstruction contains invalid values: {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_VALUES)
        except InvalidReconstructionError as exception:
            logger.error_with_traceback(exception, f"Invalid reconstruction file: {filepath}")
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_FILE)
        except IncompatibleReconstructionVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible reconstruction version: {exception.actual_version}"
                f" != expected {exception.expected_version}",
            )
            show_error_dialog(
                exception,
                TPL_RECONSTRUCTIONS_BROWSER_INCOMPATIBLE_RECONSTRUCTION_FILE.format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except DeserializationError as exception:
            logger.error_with_traceback(
                exception, f"Deserialization error while loading reconstruction from {filepath}"
            )
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_DESERIALIZATION_ERROR)
        except Exception as exception:
            logger.error_with_traceback(
                exception, f"Unexpected error while loading reconstruction data from {filepath}"
            )
            show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR)
        finally:
            self.browser_panel.unlock()

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
        self.reconstruction_panel_logic.display_reconstruction()
        self.reconstruction_details_logic.update_display()
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
        self._load_reconstruction(filepath)

    def _on_reconstruction_updated(self) -> None:
        self.reconstruction_panel_logic.update_reconstruction()
        self._unsaved_reconstruction_changes = True
        self._update_viewport_title()

    def _on_converted_reconstruction_loaded(self, filepath: Path) -> None:
        self.browser_panel.refresh()
        self._load_reconstruction_with_confirmation(filepath)

    def _close_instruction(self) -> None:
        self.instruction_panel.close_instruction()
        self._update_menu()

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
        self.reconstruction_panel_logic.close_reconstruction()
        self.reconstruction_details_logic.update_display()
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

    def _save_window_state(self) -> None:
        if self.application_config_manager.fullscreen:
            return
        viewport_x, viewport_y = dpg.get_viewport_pos()
        self.application_config_manager.set_window_state(
            fullscreen=False,
            x=int(viewport_x),
            y=int(viewport_y),
            width=dpg.get_viewport_width(),
            height=dpg.get_viewport_height(),
        )

    def _persist_application_state(self) -> None:
        self.application_config_manager.set_current_audio_device(self.audio_device_manager)
        self._save_window_state()
        self.application_config_manager.set_current_tab(self._get_current_tab())
        self.application_config_manager.save_config()

    def _play_from_start(self) -> None:
        current_tab_tag = self._get_current_tab()
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            self.reconstruction_panel.play()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            self.instruction_panel.player_panel.play()

        self._update_menu()

    def _play(self) -> None:
        current_tab_tag = self._get_current_tab()
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            self.reconstruction_panel.pause_or_resume()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            self.instruction_panel.player_panel.pause_or_resume()

        self._update_menu()

    def _stop(self) -> None:
        current_tab_tag = self._get_current_tab()
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            self.reconstruction_panel.stop()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            self.instruction_panel.player_panel.stop()

        self._update_menu()

    def _get_play_label(self) -> str:
        current_tab_tag = self._get_current_tab()
        playing = False
        loaded = False
        paused = False
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            playing = self.reconstruction_panel.is_playing()
            paused = self.reconstruction_panel.is_paused()
            loaded = self.reconstruction_panel.is_loaded()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            playing = self.instruction_panel.player_panel.is_playing()
            paused = self.instruction_panel.player_panel.is_paused()
            loaded = self.instruction_panel.player_panel.is_loaded()

        is_playing = loaded and playing
        if is_playing:
            return LBL_MENU_ITEM_PLAYBACK_RESUME if paused else LBL_MENU_ITEM_PLAYBACK_PAUSE

        return LBL_MENU_ITEM_PLAYBACK_PLAY

    def _is_play_or_pause_enabled(self) -> bool:
        current_tab_tag = self._get_current_tab()
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            return self.reconstruction_panel.is_loaded()

        if current_tab_tag == TAG_TAB_INSTRUCTIONS:
            return self.instruction_panel.player_panel.is_loaded()

        return False

    def _is_stop_enabled(self) -> bool:
        current_tab_tag = self._get_current_tab()
        loaded = False
        playing = False
        if current_tab_tag == TAG_TAB_RECONSTRUCTIONS:
            loaded = self.reconstruction_panel.is_loaded()
            playing = self.reconstruction_panel.is_playing()
        elif current_tab_tag == TAG_TAB_INSTRUCTIONS:
            loaded = self.instruction_panel.player_panel.is_loaded()
            playing = self.instruction_panel.player_panel.is_playing()

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
        return self.converter_logic.is_running()

    def _is_library_generating(self) -> bool:
        return self.library_panel.is_library_generating()

    def _is_reconstruction_unsaved(self) -> bool:
        return self._unsaved_reconstruction_changes

    def _exit_application(self) -> None:
        CallbackQueue.stop()
        self.audio_device_manager.stop()
        self.converter_logic.cleanup()

        dpg.stop_dearpygui()

    def _enable_fullscreen(self) -> None:
        dpg.set_viewport_decorated(False)

        window_x = self.application_config_manager.window_x
        window_y = self.application_config_manager.window_y
        window_width = None
        window_height = None

        monitor = self._monitor_for_position(window_x, window_y)
        if monitor is not None:
            window_x = int(monitor.x)
            window_y = int(monitor.y)
            window_width = int(monitor.width)
            window_height = int(monitor.height)
        else:
            screen_dimensions = self._get_screen_dimensions()
            window_width = screen_dimensions[0]
            window_height = screen_dimensions[1]

        self._apply_window_state(
            fullscreen=True,
            x=window_x,
            y=window_y,
            width=window_width,
            height=window_height,
        )

    def _disable_fullscreen(self) -> None:
        window_width = self.application_config_manager.window_width
        window_height = self.application_config_manager.window_height
        window_x = self.application_config_manager.window_x
        window_y = self.application_config_manager.window_y

        monitor = self._monitor_for_position(window_x, window_y)
        if monitor is not None:
            screen_x = int(monitor.x)
            screen_y = int(monitor.y)
            screen_w = int(monitor.width)
            screen_h = int(monitor.height)

            window_width = min(window_width, screen_w)
            window_height = min(window_height, screen_h)

            window_x = max(0, screen_x, min(window_x, screen_x + screen_w - window_width))
            window_y = max(0, screen_y, min(window_y, screen_y + screen_h - window_height))
        else:
            window_x = max(0, window_x)
            window_y = max(0, window_y)

        self._apply_window_state(
            fullscreen=False,
            x=window_x,
            y=window_y,
            width=window_width,
            height=window_height,
        )

        dpg.set_viewport_decorated(True)

    def _apply_window_state(
        self,
        fullscreen: bool,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        dpg.set_viewport_pos([x, y])
        dpg.set_viewport_width(width)
        dpg.set_viewport_height(height)

        self.application_config_manager.set_window_state(
            fullscreen=fullscreen,
            x=x,
            y=y,
            width=width,
            height=height,
        )

        self._update_fullscreen_menu_item()

    def _toggle_fullscreen(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        if not self.application_config_manager.config.window.fullscreen:
            self._enable_fullscreen()
        else:
            self._disable_fullscreen()

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
        self.application_config_manager.toggle_show_advanced_settings()
        self._update_advanced_settings_menu_item()

    def _update_advanced_settings_menu_item(self) -> None:
        advanced_settings = self.application_config_manager.advanced_settings
        self.advanced_settings_panel.set_visibility(advanced_settings)
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

    @staticmethod
    def _get_screen_dimensions() -> Tuple[int, int]:
        _root = tkinter.Tk()
        _root.withdraw()
        window_width = int(_root.winfo_screenwidth())
        window_height = int(_root.winfo_screenheight())
        _root.destroy()
        return window_width, window_height

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
            self.converter_logic.cleanup()
            self.config_manager.save_config()
            self._persist_application_state()
            self.audio_device_manager.terminate()
            dpg.destroy_context()
