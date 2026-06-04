from pathlib import Path
from typing import Any, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
)
from sampletones_application.categories.elements.reconstructions import (
    ReconstructionPanelElements,
    ReconstructionsBrowserElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.application.manager import SessionManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    TAG_GLOBAL_DIALOG_CONFIG_STATUS,
    TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
    TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED,
    TAG_GLOBAL_STATUS_WINDOW,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.coordinators.instructions import (
    InstructionsTabCoordinator,
)
from sampletones_application.coordinators.main import MainTabCoordinator
from sampletones_application.coordinators.playback import (
    AudioPlayerPanelProtocol,
    PlaybackRouter,
)
from sampletones_application.coordinators.reconstructions import (
    ReconstructionsTabCoordinator,
)
from sampletones_application.coordinators.sequencer import (
    SequencerTabCoordinator,
)
from sampletones_application.layout import LayoutConfig, load_layout_config
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.logic.reconstruction.browser_manager import (
    BrowserManager,
)
from sampletones_application.logic.reconstruction.manager import (
    ReconstructionManager,
)
from sampletones_application.logic.reconstruction.regenerator import Regenerator
from sampletones_application.logic.reconstruction.session import (
    ReconstructionSession,
)
from sampletones_application.paths import BEHAVIOR_DIRECTORY, LANG_EN, LAYOUT_DIRECTORY
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.menu import MenuBar
from sampletones_application.ui.panels.settings import GUIAudioSettingsWindow
from sampletones_application.ui.themes.converter import ConverterTheme
from sampletones_application.ui.themes.default import DefaultTheme
from sampletones_application.ui.themes.fps import FPSTimerTheme
from sampletones_application.ui.themes.graphs.indicator import (
    IndicatorGraphTheme,
)
from sampletones_application.ui.themes.graphs.overlay import OverlayGraphTheme
from sampletones_application.ui.themes.graphs.zero import ZeroLineGraphTheme
from sampletones_application.ui.themes.input import InvalidInputTheme
from sampletones_application.ui.themes.nodes.favorite import (
    FavoriteChildNodeTheme,
    FavoriteNodeTheme,
)
from sampletones_application.ui.themes.nodes.file import (
    LibraryFileNodeTheme,
    NoContentFileNodeTheme,
    NotExpandedDirectoryNodeTheme,
    ReconstructionFileNodeTheme,
    WaveFileNodeTheme,
)
from sampletones_application.ui.themes.nodes.library import (
    LibraryGeneratorNodeTheme,
    LibraryGroupNodeTheme,
    LibraryInstructionNodeTheme,
    LibraryLibraryNodeTheme,
)
from sampletones_application.ui.themes.status import StatusBarTheme
from sampletones_application.ui.themes.tables.initial_pitch import (
    InitialPitchTableTheme,
)
from sampletones_application.ui.themes.tables.pattern import PatternTableTheme
from sampletones_application.ui.themes.tables.table import TableTheme
from sampletones_application.ui.themes.trace import TracebackTheme
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.dpg import dpg_set_value
from sampletones_application.utils.file import file_dialog_handler
from sampletones_application.utils.fps import FPSTimer
from sampletones_application.utils.shortcuts.ids import ShortcutId
from sampletones_application.utils.shortcuts.keys import Modifier
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.utils.shortcuts.shortcut import Shortcut
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_application.viewport import ViewportManager
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.paths import (
    EXT_FILE_JSON,
    EXT_FILE_RECONSTRUCTION,
    EXT_FILES_AUDIO,
)
from sampletones_core.sequencer import Sequencer
from sampletones_shared.exceptions import LoadReconstructionError
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback


class Application:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.layout: LayoutConfig = load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY)
        self.language_manager: LanguageManager = LanguageManager(LANG_EN)
        self.dialogs: DialogsRenderer = DialogsRenderer(
            layout=self.layout.general, language_manager=self.language_manager
        )
        self._setup_themes()
        self.audio_device_manager: AudioDeviceManager = AudioDeviceManager()
        self.config_manager = ConfigManager(config_path, dialogs=self.dialogs)
        self.session_manager = SessionManager()
        self.shortcut_manager: ShortcutManager = ShortcutManager()

        self.library_manager = InstructionsLibraryManager(
            self.config_manager,
            language_manager=self.language_manager,
        )
        self.browser_manager = BrowserManager(
            self.config_manager,
            language_manager=self.language_manager,
        )
        self.reconstruction_manager = ReconstructionManager(
            scheduling=self.layout.behavior.scheduling,
        )
        self.regenerator: Regenerator = Regenerator(
            self.reconstruction_manager,
            scheduling=self.layout.behavior.scheduling,
        )
        self.sequencer: Sequencer = Sequencer()

        self.fps_timer: FPSTimer = FPSTimer()

        self.audio_settings_window: GUIAudioSettingsWindow = GUIAudioSettingsWindow(
            self.audio_device_manager,
            layout=self.layout.settings,
            language_manager=self.language_manager,
        )
        self.status_bar = GUIStatusBar(
            display_time=self.layout.behavior.ui.status_bar_display_time,
        )
        self.theme = DefaultTheme()
        self.fps_theme = FPSTimerTheme()

        self._reconstruction_session = ReconstructionSession()

        self._menu_bar = MenuBar(
            shortcut_manager=self.shortcut_manager,
            fps_theme=self.fps_theme,
            language_manager=self.language_manager,
        )

        self._viewport_manager = ViewportManager(
            self.session_manager,
            self.theme,
            layout=self.layout.general,
            on_fullscreen_state_changed=self._update_menu,
        )

        self._main_tab = MainTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            library_manager=self.library_manager,
            on_reconstruct_file=self._reconstruct_file,
            on_reconstruct_directory=self._reconstruct_directory,
            on_load_reconstruction=self._load_reconstruction_with_confirmation,
            on_load_library=self._load_library,
            is_generation_in_progress=self._is_generation_in_progress,
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
        )

        self._reconstructions_tab = ReconstructionsTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
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
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
        )

        self._instructions_tab = InstructionsTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            library_manager=self.library_manager,
            on_audio_state_changed=self._update_menu,
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
        )

        self._sequencer_tab = SequencerTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            browser_manager=self.browser_manager,
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
        )

        self._playback_router = PlaybackRouter(
            current_player_fn=self._get_current_player,
            language_manager=self.language_manager,
        )

        self._reconstruction_session.on_state_changed = self._on_reconstruction_state_changed

        self._setup_gui()
        self._load_settings()

    def _load_settings(self) -> None:
        audio_device = self.session_manager.current_audio_device
        buffer_size = self.session_manager.current_buffer_size
        self.audio_device_manager.set_current_device(audio_device)
        self.audio_device_manager.set_buffer_size(buffer_size)

    def _setup_themes(self) -> None:
        general = self.layout.general
        graphs = self.layout.graphs
        instructions = self.layout.instructions
        reconstructions = self.layout.reconstructions
        sequencer = self.layout.sequencer

        FontRegistry.setup(general.fonts)

        DefaultTheme.setup(general)
        StatusBarTheme.setup(general)
        FPSTimerTheme.setup(general)
        ConverterTheme.setup(general)
        InvalidInputTheme.setup(general)
        TracebackTheme.setup(general)
        TableTheme.setup(general)

        FavoriteNodeTheme.setup(general)
        FavoriteChildNodeTheme.setup(general)
        NoContentFileNodeTheme.setup(general)
        ReconstructionFileNodeTheme.setup(general)
        LibraryFileNodeTheme.setup(general)
        WaveFileNodeTheme.setup(general)
        NotExpandedDirectoryNodeTheme.setup(general)

        LibraryLibraryNodeTheme.setup(instructions)
        LibraryGeneratorNodeTheme.setup(instructions)
        LibraryGroupNodeTheme.setup(instructions)
        LibraryInstructionNodeTheme.setup(instructions)

        IndicatorGraphTheme.setup(graphs)
        OverlayGraphTheme.setup(graphs)
        ZeroLineGraphTheme.setup(graphs)

        InitialPitchTableTheme.setup(reconstructions)
        PatternTableTheme.setup(general, sequencer)

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

    def _set_fonts(self) -> None:
        FontRegistry.register_fonts(self.layout.general.fonts.scale)

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
            label=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.MAIN_WINDOW,
                )
            ],
            tag=TAG_GLOBAL_WINDOW_MAIN,
        ):
            self._create_menu_bar()
            self._create_tabs()
            self._create_status_bar()

        dpg.set_primary_window(TAG_GLOBAL_WINDOW_MAIN, True)

    def _create_menu_bar(self) -> None:
        self._menu_bar.create(self._build_menu_bar_viewmodel())

    def _build_menu_bar_viewmodel(self) -> MenuBarViewModel:
        return MenuBarViewModel(
            reconstruction_loaded=self._is_reconstruction_loaded(),
            play_label=self._playback_router.play_label,
            play_or_pause_enabled=self._playback_router.is_play_enabled,
            stop_enabled=self._playback_router.is_stop_enabled,
            autoplay=self.session_manager.autoplay,
            fullscreen=self.session_manager.fullscreen,
            advanced_settings=self.session_manager.advanced_settings,
        )

    def _update_menu(self) -> None:
        self._main_tab.sync_advanced_settings_visibility()
        self._menu_bar.update(self._build_menu_bar_viewmodel())

    def _create_tabs(self) -> None:
        with dpg.child_window(
            height=-self.layout.general.status_bar.height,
            border=False,
        ):
            with dpg.tab_bar(
                tag=TAG_GLOBAL_TABS,
                callback=self._on_tab_changed,
            ):
                self._main_tab.create_tab()
                self._reconstructions_tab.create_tab()
                self._sequencer_tab.create_tab()
                self._instructions_tab.create_tab()

    def _create_status_bar(self) -> None:
        with dpg.child_window(
            tag=TAG_GLOBAL_STATUS_WINDOW,
            parent=TAG_GLOBAL_WINDOW_MAIN,
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
        current_tab = self.session_manager.load_current_tab()
        if dpg.does_alias_exist(current_tab) and dpg.does_item_exist(current_tab):
            dpg.set_value(TAG_GLOBAL_TABS, current_tab)

        current_reconstruction = self.session_manager.current_reconstruction
        if current_reconstruction is not None:
            if current_reconstruction.exists():
                try:
                    self.reconstruction_manager.load_reconstruction(current_reconstruction)
                except LoadReconstructionError:
                    self.session_manager.set_current_reconstruction(None)
            else:
                self.session_manager.set_current_reconstruction(None)

    def _save_reconstruction_as_dialog(self) -> None:
        filepath = self.reconstruction_manager.filepath
        if filepath is None:
            return

        with dpg.file_dialog(
            label=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.SAVE_RECONSTRUCTION,
                )
            ],
            width=self.layout.general.dialogs.file.width,
            height=self.layout.general.dialogs.file.height,
            callback=self._handle_save_reconstruction_as,
            file_count=1,
            default_filename=filepath.name,
            default_path=str(filepath.parent),
        ):
            dpg.add_file_extension(EXT_FILE_RECONSTRUCTION)

    def _save_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.SAVE_CONFIG,
                )
            ],
            width=self.layout.general.dialogs.file.width,
            height=self.layout.general.dialogs.file.height,
            callback=self._handle_save_config,
            file_count=1,
            default_filename="config",
            default_path=str(self.session_manager.get_config_path()),
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    @file_dialog_handler
    def _handle_save_config(self, filepath: Path) -> None:
        try:
            self.config_manager.save_config_to_file(filepath)
            self._show_config_status_dialog(
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.CONFIGURATION_SAVED_SUCCESSFULLY,
                    )
                ]
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save config to {filepath}")
            self.dialogs.show_error(
                exception,
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.CONFIG_SAVE_FAILED,
                    )
                ],
            )

        self.session_manager.set_config_path(filepath)

    @file_dialog_handler
    def _handle_save_reconstruction_as(self, filepath: Path) -> None:
        try:
            self._save_reconstruction(filepath)
            self.dialogs.show_info(
                TAG_GLOBAL_DIALOG_RECONSTRUCTION_SAVED,
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.RECONSTRUCTION_SAVED_SUCCESSFULLY,
                    )
                ],
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.TITLE,
                        GlobalDialogTitleElements.RECONSTRUCTION_SAVED,
                    )
                ],
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save reconstruction to {filepath}")
            self.dialogs.show_error(
                exception,
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.RECONSTRUCTION_SAVE_FAILED,
                    )
                ],
            )

        self.session_manager.set_reconstruction_path(filepath)

    def _load_config_dialog(self) -> None:
        with dpg.file_dialog(
            label=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.LOAD_CONFIG,
                )
            ],
            width=self.layout.general.dialogs.file.width,
            height=self.layout.general.dialogs.file.height,
            callback=self._handle_load_config,
            file_count=1,
            default_path=str(self.session_manager.get_config_path()),
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    @file_dialog_handler
    def _handle_load_config(self, filepath: Path) -> None:
        try:
            self.config_manager.load_config_from_file(filepath)
            self._show_config_status_dialog(
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.CONFIGURATION_LOADED_SUCCESSFULLY,
                    )
                ]
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to load config from {filepath}")
            self.dialogs.show_error(
                exception,
                self.language_manager[
                    TextKey(
                        Page.RECONSTRUCTIONS,
                        Panel.RECONSTRUCTION,
                        TextType.MESSAGE,
                        ReconstructionPanelElements.EXPORT_WAV_FAILED,
                    )
                ],
            )

        self.session_manager.set_config_path(filepath)

    def _open_audio_settings(self) -> None:
        self.audio_settings_window.show()

    def _reconstruct_file_dialog(self) -> None:
        if self._main_tab.is_converter_running():
            logger.warning("A conversion is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()
        with dpg.file_dialog(
            label=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.RECONSTRUCT_FILE,
                )
            ],
            width=self.layout.general.dialogs.file.width,
            height=self.layout.general.dialogs.file.height,
            callback=self._handle_reconstruct_file,
            file_count=1,
            default_path=str(self.session_manager.get_reconstruction_path()),
        ):
            all_file_extensions = ",".join(EXT_FILES_AUDIO)
            key = TextKey(
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.MESSAGE,
                GlobalMessageElements.ALL_AUDIO_FORMATS,
            )
            dpg.add_file_extension(
                f"{self.language_manager[key]}{{{all_file_extensions}}}",
                color=(0, 255, 255, 255),
            )
            for extension in EXT_FILES_AUDIO:
                dpg.add_file_extension(extension)

    def _reconstruct_directory_dialog(self) -> None:
        if self._main_tab.is_converter_running():
            logger.warning("A conversion is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()
        dpg.add_file_dialog(
            label=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.RECONSTRUCT_DIRECTORY,
                )
            ],
            width=self.layout.general.dialogs.file.width,
            height=self.layout.general.dialogs.file.height,
            callback=self._handle_reconstruct_directory,
            directory_selector=True,
            default_path=str(self.session_manager.get_reconstruction_path()),
            show=True,
        )

    def _load_reconstruction_dialog(self) -> None:
        with dpg.file_dialog(
            label=self.language_manager[
                TextKey(
                    Page.RECONSTRUCTIONS,
                    Panel.BROWSER,
                    TextType.TITLE,
                    ReconstructionsBrowserElements.LOAD_RECONSTRUCTION_DIALOG,
                )
            ],
            width=self.layout.general.dialogs.file.width,
            height=self.layout.general.dialogs.file.height,
            callback=self._handle_load_reconstruction,
            file_count=1,
            default_path=str(self.session_manager.get_reconstruction_path()),
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
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.TITLE,
                        GlobalDialogTitleElements.LOAD_UNSAVED_RECONSTRUCTION,
                    )
                ],
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.LOAD_UNSAVED_RECONSTRUCTION,
                    )
                ],
                on_confirm=load_reconstruction,
                on_save=self._save_reconstruction,
                ok_label=self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.LABEL,
                        DialogElements.DISCARD,
                    )
                ],
            )
        else:
            load_reconstruction()

    def _show_config_status_dialog(self, message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent)

        self.dialogs.show_modal(
            tag=TAG_GLOBAL_DIALOG_CONFIG_STATUS,
            title=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.CONFIG_STATUS,
                )
            ],
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
            self.dialogs.show_reconstruction_not_loaded()
            return False

        return True

    def _is_reconstruction_loaded(self) -> bool:
        return self.reconstruction_manager.is_reconstruction_loaded()

    def _reconstruct_file(self, filepath: Path) -> None:
        self._main_tab.set_input_path(filepath, convert=True)
        self.session_manager.set_reconstruction_path(filepath.parent)
        self._set_current_tab(Tab.MAIN)
        self._update_menu()

    def _load_library(self, filepath: Path) -> None:
        self._instructions_tab.load_library_file(filepath)
        self.config_manager.update_gui()
        self._set_current_tab(Tab.INSTRUCTIONS)
        self._update_menu()

    @file_dialog_handler
    def _handle_reconstruct_file(self, filepath: Path) -> None:
        self._reconstruct_file(filepath)

    def _reconstruct_directory(self, directory_path: Path) -> None:
        self._main_tab.set_input_path(directory_path, convert=True)
        self.session_manager.set_reconstruction_path(directory_path)
        self._set_current_tab(Tab.MAIN)
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
            self.dialogs.show_file_not_found(
                reconstruction_data.reconstruction.audio_filepath,
                self.language_manager[
                    TextKey(
                        Page.RECONSTRUCTIONS,
                        Panel.BROWSER,
                        TextType.MESSAGE,
                        ReconstructionsBrowserElements.AUDIO_FILE_NOT_FOUND,
                    )
                ],
            )

        filepath = reconstruction_data.filepath
        self.config_manager.load_library_and_generation_config(reconstruction_data.config)
        self._reconstructions_tab.display_reconstruction()
        self.session_manager.set_current_reconstruction(filepath)

        self._set_current_tab(Tab.RECONSTRUCTIONS)
        self._reconstruction_session.mark_loaded(filepath.stem)

    def _on_playback_error(self, exception: Exception) -> None:
        logger.error_with_traceback(exception, "Playback error occurred")
        self.dialogs.show_error(
            exception,
            self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.AUDIO_PLAYBACK_ERROR,
                )
            ],
        )

    @file_dialog_handler
    def _handle_load_reconstruction(self, filepath: Path) -> None:
        self.session_manager.set_reconstruction_path(filepath.parent)
        self._reconstructions_tab.load_reconstruction(filepath)

    def _on_reconstruction_updated(self) -> None:
        self._reconstructions_tab.update_reconstruction()
        self._reconstruction_session.mark_updated()

    def _on_converted_reconstruction_loaded(self, filepath: Path) -> None:
        self._reconstructions_tab.refresh_browser()
        self._load_reconstruction_with_confirmation(filepath)

    def _save_reconstruction(self, filepath: Optional[Path] = None) -> None:
        self.reconstruction_manager.save_reconstruction(filepath)
        self._reconstruction_session.mark_saved(filepath.stem if filepath is not None else None)

    def _close_reconstruction_with_confirmation(self) -> None:
        if self._is_reconstruction_unsaved():
            self._show_save_confirmation_dialog(
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.TITLE,
                        GlobalDialogTitleElements.CLOSE_UNSAVED_RECONSTRUCTION,
                    )
                ],
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.CLOSE_UNSAVED_RECONSTRUCTION,
                    )
                ],
                on_confirm=self._close_reconstruction,
                on_save=self._save_reconstruction,
                ok_label=self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.LABEL,
                        DialogElements.CLOSE,
                    )
                ],
            )
        else:
            self._close_reconstruction()

    def _close_reconstruction(self) -> None:
        self.reconstruction_manager.close_reconstruction()

    def _on_reconstruction_closed(self) -> None:
        self._reconstructions_tab.close_reconstruction()
        self.session_manager.set_current_reconstruction(None)
        self._reconstruction_session.mark_closed()

    def _on_reconstruction_state_changed(self) -> None:
        self._viewport_manager.update_title(
            self._reconstruction_session.name,
            self._reconstruction_session.unsaved_changes,
            title=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.MAIN_WINDOW,
                )
            ],
        )
        self._update_menu()

    def _set_current_tab(self, tab_tag: str) -> None:
        dpg_set_value(TAG_GLOBAL_TABS, tab_tag)
        self.session_manager.set_current_tab(tab_tag)

    def _get_current_tab(self) -> str:
        current_tab = dpg.get_value(TAG_GLOBAL_TABS)
        alias: str = dpg.get_item_alias(current_tab)
        return alias

    def _get_current_player(self) -> Optional[AudioPlayerPanelProtocol]:
        match self._get_current_tab():
            case Tab.RECONSTRUCTIONS:
                return self._reconstructions_tab.player_panel
            case Tab.INSTRUCTIONS:
                return self._instructions_tab.player_panel
            case _:
                return None

    def _persist_application_state(self) -> None:
        self.session_manager.set_current_audio_device(self.audio_device_manager)
        self._viewport_manager.save_window_state()
        self.session_manager.set_current_tab(self._get_current_tab())
        self.session_manager.save_config()

    def _play_from_start(self) -> None:
        self._playback_router.play_from_start()
        self._update_menu()

    def _play(self) -> None:
        self._playback_router.play()
        self._update_menu()

    def _stop(self) -> None:
        self._playback_router.stop()
        self._update_menu()

    def _toggle_fullscreen(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self._viewport_manager.toggle_fullscreen()

    def _toggle_autoplay(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self.session_manager.toggle_autoplay()
        self._update_menu()

    def _toggle_advanced_settings(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self._main_tab.toggle_advanced_settings()
        self._update_menu()

    def _update_fps(self, delta_time: float) -> None:
        fps = self.fps_timer.update(delta_time)
        self._menu_bar.update_fps(fps)

    def _show_confirmation_dialog(
        self,
        message: str,
        ok_label: str,
    ) -> None:
        self.dialogs.show_confirmation(
            tag=TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
            title=self.language_manager[
                TextKey(
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.TITLE,
                    GlobalDialogTitleElements.EXIT_CONFIRMATION,
                )
            ],
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
        ok_label: str,
    ) -> None:
        self.dialogs.show_save_confirmation(
            tag=TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
            title=title,
            message=message,
            on_save=on_save,
            on_confirm=on_confirm,
            ok_label=ok_label,
        )

    def _on_close(self) -> None:
        if self._is_reconstruction_unsaved():
            self._show_save_confirmation_dialog(
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.TITLE,
                        GlobalDialogTitleElements.EXIT_CONFIRMATION,
                    )
                ],
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.EXIT_UNSAVED_RECONSTRUCTION,
                    )
                ],
                on_save=self._save_reconstruction,
                on_confirm=self._exit_application,
                ok_label=self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.LABEL,
                        DialogElements.EXIT,
                    )
                ],
            )
        elif self._is_converter_running():
            self._show_confirmation_dialog(
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.EXIT_CONVERSION_IN_PROGRESS,
                    )
                ],
                ok_label=self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.LABEL,
                        DialogElements.EXIT,
                    )
                ],
            )
        elif self._is_library_generating():
            self._show_confirmation_dialog(
                self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.MESSAGE,
                        GlobalMessageElements.EXIT_LIBRARY_GENERATION_IN_PROGRESS,
                    )
                ],
                ok_label=self.language_manager[
                    TextKey(
                        Page.GLOBAL,
                        Panel.DIALOG,
                        TextType.LABEL,
                        DialogElements.EXIT,
                    )
                ],
            )
        else:
            self._exit_application()

    def _is_converter_running(self) -> bool:
        return self._main_tab.is_converter_running()

    def _is_library_generating(self) -> bool:
        return self._instructions_tab.is_library_generating()

    def _is_reconstruction_unsaved(self) -> bool:
        return self._reconstruction_session.unsaved_changes

    def _exit_application(self) -> None:
        CallbackQueue.stop()
        self.audio_device_manager.stop()
        self._main_tab.converter_logic.cleanup()

        dpg.stop_dearpygui()

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
        CallbackQueue.add(
            self._update_status,
            priority=self.layout.behavior.scheduling.priority_update_status,
        )

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
