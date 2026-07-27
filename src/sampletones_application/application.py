from pathlib import Path
from typing import Any, Final, Optional

import dearpygui.dearpygui as dpg
from pydantic import ValidationError

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    FileFilterElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
    GlobalTemplateElements,
    MenuElements,
    StatusElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.deployment.deployment import (
    DeploymentConfig,
)
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.config import ConfigCoordinator
from sampletones_application.coordinators.original_audio import OriginalAudioLocator
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.coordinators.playback.router import PlaybackRouter
from sampletones_application.coordinators.project import ProjectCoordinator
from sampletones_application.coordinators.reconstruction import (
    ReconstructionCoordinator,
)
from sampletones_application.coordinators.tabs.instructions import InstructionsTabCoordinator
from sampletones_application.coordinators.tabs.main import MainTabCoordinator
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.coordinators.tabs.sequencer import SequencerTabCoordinator
from sampletones_application.layout import LayoutConfig, load_layout_config
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.project.title.compose import window_title
from sampletones_application.logic.project.title.document import (
    ReconstructionTitlePart,
    document_title,
)
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.parameters import (
    InstructionsTabParameters,
    MainTabParameters,
    ReconstructionTabParameters,
    SequencerTabParameters,
)
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    DEPLOYMENT_CONFIG_PATH,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTE_PATH,
    THEME_DIRECTORY,
)
from sampletones_application.services import (
    ConversionService,
    ExportService,
    RegeneratedInstrument,
    RegenerationService,
    RetunedSample,
    RetuneResult,
    SampleRetuneService,
    ServiceCancelled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_application.shell import ApplicationShell, ShortcutBindings
from sampletones_application.tags.general import (
    TAG_GLOBAL_DIALOG_ABOUT,
    TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_MENU_FPS,
    TAG_GLOBAL_THEME_PLAYER_BUTTON,
    TAG_GLOBAL_THEME_PLAYER_TOOLBAR,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.table.caret import CaretOverlay
from sampletones_application.ui.menu import MenuBar
from sampletones_application.ui.panels.dialogs.audio_settings import (
    GUIAudioSettingsWindow,
)
from sampletones_application.ui.panels.dialogs.project_properties import (
    GUIProjectPropertiesWindow,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.file_dialogs.api import (
    open_file_dialog,
    select_directory_dialog,
)
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.fps import FPSTimer
from sampletones_application.utils.frame_limiter import FrameLimiter
from sampletones_application.utils.gui.dialogs import DialogsRenderer, get_dialog_tag
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.palette import Palette
from sampletones_application.utils.parallelization.background import (
    stop_background_workers,
)
from sampletones_application.view_model.shared.audio_settings import (
    AudioSettingsViewModel,
)
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_application.view_model.shared.project_properties import (
    ProjectPropertiesViewModel,
)
from sampletones_application.viewport import ViewportManager
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.audio import BufferSize, SampleRate
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.paths import EXT_FILES_AUDIO
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.types.feature import FeatureValue
from sampletones_shared.application import (
    SAMPLETONES_AUTHOR,
    SAMPLETONES_GROUP,
    SAMPLETONES_NAME_VERSION,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender

SEQUENCER_SAMPLE_TITLE_FORMAT: Final[str] = "{ordinal}: {name}"
SEQUENCER_SAMPLE_ORDINAL_FORMAT: Final[str] = "02X"


class Application:
    """
    The composition root of the SampleToNES GUI application.

    ``Application.__init__`` is the only place where components are created and
    wired together — this concentration makes the dependency graph visible and
    eliminates hidden coupling.

    Responsibilities and principles of the ``Application class:
    - It contains no domain logic.
    - It forwards events between coordinators.
    - It mediates mutual dependencies between them.
    - It persists session state on exit.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        library_path: Optional[Path] = None,
        reconstruction_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> None:
        self.deployment: DeploymentConfig = DeploymentConfig.load(DEPLOYMENT_CONFIG_PATH)
        self._set_logging_level()

        self._palette: Palette = Palette.load(PALETTE_PATH)
        self.layout: LayoutConfig = self._load_layout_config()
        self._setup_gui_elements()

        self.language_manager: LanguageManager = LanguageManager(LANG_EN)

        self.status_bar = GUIStatusBar(
            display_time=self.layout.behavior.ui.status_bar_display_time,
        )
        self.key_router: KeyRouter = KeyRouter()
        self.shortcut_manager: ShortcutManager = ShortcutManager(key_router=self.key_router)
        self.dialogs: DialogsRenderer = DialogsRenderer(
            layout=self.layout.general,
            language_manager=self.language_manager,
            status_bar=self.status_bar,
            key_router=self.key_router,
        )
        self.audio_device_manager: AudioDeviceManager = AudioDeviceManager()
        self.config_manager = ConfigManager(config_path)
        self.session_manager = SessionManager()

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

        _priority = self.layout.behavior.scheduling.priorities.schedule
        self.conversion_service: ConversionService = ConversionService(priority=_priority)
        self.regeneration_service: RegenerationService = RegenerationService(priority=_priority)
        self.export_service: ExportService = ExportService(priority=_priority)
        self.retune_service: SampleRetuneService = SampleRetuneService(priority=_priority)
        self.retune_service.subscribe(self._on_retune_result)

        self.project_manager: ProjectManager = ProjectManager()
        self.project_controller: ProjectController = ProjectController(self.project_manager)
        self.history: HistoryManager = HistoryManager(
            self.project_controller,
            budget=self.session_manager.history_budget,
            strict=self.deployment.strict_history,
        )
        self.project_controller.on_mutation = self.history.handle_mutation
        self.project_controller.on_saved = self.history.mark_saved
        self.history.on_history_changed = self._on_history_changed

        self.fps_timer: FPSTimer = FPSTimer(interval=self.layout.behavior.main.fps_update_interval)
        self.frame_limiter: FrameLimiter = FrameLimiter(self.layout.behavior.main.max_fps)
        self._audio_was_playing: bool = False

        self.audio_settings_window: GUIAudioSettingsWindow = GUIAudioSettingsWindow(
            layout=self.layout.settings,
            language_manager=self.language_manager,
            key_router=self.key_router,
        )
        self.audio_settings_window.on_commit = self._apply_audio_settings
        self.audio_settings_window.on_refresh_devices = self._refresh_audio_devices
        self.audio_settings_window.on_master_gain_changed = self.session_manager.set_master_gain
        self.project_properties_window: GUIProjectPropertiesWindow = GUIProjectPropertiesWindow(
            layout=self.layout.project_properties,
            language_manager=self.language_manager,
            key_router=self.key_router,
        )
        self.project_properties_window.on_commit = self._commit_project_properties
        self.theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT)
        self.fps_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_MENU_FPS)
        self.player_toolbar_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_PLAYER_TOOLBAR)
        self.player_button_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_PLAYER_BUTTON)

        self._menu_bar = MenuBar(
            shortcut_manager=self.shortcut_manager,
            fps_theme=self.fps_theme,
            player_toolbar_theme=self.player_toolbar_theme,
            player_button_theme=self.player_button_theme,
            player_glyphs=self.layout.glyphs.player,
            player_layout=self.layout.player,
            language_manager=self.language_manager,
            on_play_from_start=self._play_from_start,
            on_pause_or_resume=self._play,
            on_stop=self._stop,
        )

        self._viewport_manager = ViewportManager(
            self.session_manager,
            self.theme,
            min_width=self.layout.general.window.min_width,
            min_height=self.layout.general.window.min_height,
            vsync=self.layout.behavior.main.vsync,
            on_fullscreen_state_changed=self._update_menu,
        )

        self._project_coordinator = ProjectCoordinator(
            self.project_controller,
            self.project_manager,
            self.session_manager,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
            on_tab_switch=self._set_current_tab,
            on_session_state_changed=self._on_project_state_changed,
        )

        self._reconstruction_coordinator = ReconstructionCoordinator(
            self.reconstruction_manager,
            self.session_manager,
            self.regeneration_service,
            self.audio_device_manager,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
            on_tab_switch=self._set_current_tab,
            on_session_state_changed=self._on_reconstruction_state_changed,
            on_reconstruction_updated=self._on_reconstruction_updated,
            is_reconstruction_embedded=self._editing_project_sample,
        )

        self._original_audio_locator = OriginalAudioLocator(
            dialogs=self.dialogs,
            language_manager=self.language_manager,
        )

        self._reconstructions_tab = ReconstructionTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            reconstruction_manager=self.reconstruction_manager,
            browser_manager=self.browser_manager,
            export_service=self.export_service,
            on_load_reconstruction_with_confirmation=self._reconstruction_coordinator.load_with_confirmation,
            on_reconstruct_file=self._reconstruct_file_dialog,
            on_reconstruct_directory=self._reconstruct_directory_dialog,
            on_change_audio_state=self._update_menu,
            on_reconstruction_instrument_updated=self._regenerate_instrument,
            is_operation_active=self._is_operation_active,
            original_audio_locator=self._original_audio_locator,
            layout=ReconstructionTabParameters.from_config(self.layout),
            language_manager=self.language_manager,
            dialogs=self.dialogs,
            status_bar=self.status_bar,
        )

        self._reconstruction_coordinator.set_reconstructions_tab(self._reconstructions_tab)

        self._instructions_tab = InstructionsTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            library_manager=self.library_manager,
            on_audio_state_changed=self._update_menu,
            on_generation_state_changed=self._on_library_operation_changed,
            is_operation_active=self._is_operation_active,
            is_converter_visible=self._is_converter_panel_visible,
            layout=InstructionsTabParameters.from_config(self.layout),
            language_manager=self.language_manager,
            dialogs=self.dialogs,
            status_bar=self.status_bar,
        )

        self._main_tab = MainTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            library_manager=self.library_manager,
            conversion_service=self.conversion_service,
            on_reconstruct_file=self._reconstruct_file,
            on_reconstruct_directory=self._reconstruct_directory,
            on_load_reconstruction=self._reconstruction_coordinator.load_with_confirmation,
            on_load_library=self._load_library,
            is_operation_active=self._is_operation_active,
            on_busy_state_changed=self._refresh_busy_state,
            layout=MainTabParameters.from_config(self.layout),
            language_manager=self.language_manager,
            dialogs=self.dialogs,
            status_bar=self.status_bar,
            on_load_file=self._on_converted_reconstruction_loaded,
            on_load_directory=self._navigate_to_reconstructions,
            on_cancelled=self._refresh_reconstruction_trees,
            on_refresh_trees=self._refresh_reconstruction_trees,
            on_generate_library=self._instructions_tab.ensure_library_loaded,
        )

        self._sequencer_tab = SequencerTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            key_router=self.key_router,
            browser_manager=self.browser_manager,
            project_controller=self.project_controller,
            history=self.history,
            original_audio_locator=self._original_audio_locator,
            layout=SequencerTabParameters.from_config(self.layout),
            language_manager=self.language_manager,
            dialogs=self.dialogs,
            status_bar=self.status_bar,
            on_edit_sample_requested=self._edit_project_sample,
            on_tab_switch=self._set_current_tab,
            on_nes_frequency_changed=self._retune_samples_for_rate,
        )

        self._playback_router = PlaybackRouter(
            sources=(
                self._reconstructions_tab.player,
                self._instructions_tab.player,
                self._sequencer_tab.player,
            ),
            active_source_resolver=self._get_active_source,
            audio_device_manager=self.audio_device_manager,
            language_manager=self.language_manager,
        )

        self._config_coordinator = ConfigCoordinator(
            self.config_manager,
            self.session_manager,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
        )

        self._shell = ApplicationShell(
            session_manager=self.session_manager,
            language_manager=self.language_manager,
            shortcut_manager=self.shortcut_manager,
            key_router=self.key_router,
            layout=self.layout,
            theme=self.theme,
            viewport_manager=self._viewport_manager,
            menu_bar=self._menu_bar,
            status_bar=self.status_bar,
            fps_timer=self.fps_timer,
            main_tab=self._main_tab,
            reconstructions_tab=self._reconstructions_tab,
            sequencer_tab=self._sequencer_tab,
            instructions_tab=self._instructions_tab,
        )
        self._setup_gui()
        self._restore_current_items(
            library_path=library_path,
            reconstruction_path=reconstruction_path,
            project_path=project_path,
        )

        self._config_coordinator.present_pending_load_outcomes()
        self._load_settings()

    def _set_logging_level(self) -> None:
        logger.set_level(self.deployment.log_level.to_logging_level())

    def _load_settings(self) -> None:
        audio_device = self.session_manager.current_audio_device
        buffer_size = self.session_manager.current_buffer_size
        self.audio_device_manager.set_current_device(audio_device)
        self.audio_device_manager.set_buffer_size(buffer_size)

    def _try_load_reconstruction(self, path: Path) -> None:
        self._reconstruction_coordinator.load_reconstruction_safely(path)

    def _try_load_project(self, path: Path) -> None:
        self._project_coordinator.load_project_safely(path)

    def _try_load_library(self, path: Path) -> None:
        self._instructions_tab.load_library_safely(path)

    def _load_layout_config(self) -> LayoutConfig:
        try:
            return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, self._palette)
        except ValidationError as exception:
            raise SystemError(f"Invalid layout configuration: {exception}") from exception

    def _setup_gui_elements(self) -> None:
        FontRegistry.setup(self.layout.fonts)
        GUIPanel.configure_section_header(
            self.layout.glyphs,
            self.layout.general.section_header,
            self.layout.general.collapse,
        )

        try:
            setup_themes(THEME_DIRECTORY, self._palette)
        except ValidationError as exception:
            raise SystemError(f"Invalid theme configuration: {exception}") from exception

    def _setup_gui(self) -> None:
        bindings = self._create_shortcut_bindings()
        self._setup_shell(bindings)
        self._initialize_caret()
        self._set_callbacks()
        self._main_tab.emit_initial_view()
        self._instructions_tab.initialize()
        self._sequencer_tab.initialize()
        self.history.reset()
        self.config_manager.update_gui()
        self._update_menu()

    def _create_shortcut_bindings(self) -> ShortcutBindings:
        return ShortcutBindings(
            new_project=self._project_coordinator.new_project_with_confirmation,
            open_project=self._project_coordinator.open_with_confirmation,
            save_project=self._project_coordinator.save,
            save_project_as=self._project_coordinator.save_as_dialog,
            project_properties=self._open_project_properties,
            export_project_module=self._project_coordinator.export_module_dialog,
            close_project=self._project_coordinator.close_with_confirmation,
            exit=self._on_close,
            undo=self._sequencer_tab.undo,
            redo=self._sequencer_tab.redo,
            reconstruct_file=self._reconstruct_file_dialog,
            reconstruct_directory=self._reconstruct_directory_dialog,
            load_generation_settings=self._config_coordinator.load_dialog,
            save_generation_settings=self._config_coordinator.save_dialog,
            open_reconstruction=self._reconstruction_coordinator.load_with_confirmation,
            save_reconstruction=self._reconstruction_coordinator.save,
            save_reconstruction_as=self._reconstruction_coordinator.save_as_dialog,
            close_reconstruction=self._reconstruction_coordinator.close_with_confirmation,
            export_wav=self._export_reconstruction_wav_dialog,
            export_instruments=self._export_reconstruction_instruments_dialog,
            add_reconstruction_to_sequencer=self._add_current_reconstruction_to_sequencer,
            open_reconstruction_in_explorer=self._open_reconstruction_in_explorer,
            locate_original_audio=self._locate_original_audio,
            play=self._play,
            play_from_start=self._play_from_start,
            play_from_frame=self._play_from_frame,
            stop=self._stop,
            toggle_autoplay=self._toggle_autoplay,
            toggle_follow_playback=self._toggle_follow_playback,
            toggle_loop_song=self._toggle_loop_song,
            audio_settings=self._open_audio_settings,
            toggle_advanced_settings=self._toggle_advanced_settings,
            toggle_fullscreen=self._shell.toggle_fullscreen,
            about=self._open_about_dialog,
            next_tab=self._next_tab,
            previous_tab=self._previous_tab,
        )

    def _setup_shell(self, bindings: ShortcutBindings) -> None:
        self._shell.setup(
            bindings,
            on_close=self._on_close,
            on_tab_changed=self._on_tab_changed,
            initial_menu_state=self._build_initial_menu_state(),
        )

    def _initialize_caret(self) -> None:
        CaretOverlay.initialize(
            self.layout.general.caret,
            root_window_tag=TAG_GLOBAL_WINDOW_MAIN,
        )

    def _restore_current_items(
        self,
        library_path: Optional[Path],
        reconstruction_path: Optional[Path],
        project_path: Optional[Path],
    ) -> None:
        self._shell.restore_current_items(
            library_path=library_path,
            reconstruction_path=reconstruction_path,
            project_path=project_path,
            on_load_library=self._try_load_library,
            on_load_project=self._try_load_project,
            on_load_reconstruction=self._try_load_reconstruction,
        )

    def _set_callbacks(self) -> None:
        self.config_manager.add_config_change_callback(self._update_menu)
        self.audio_device_manager.set_callbacks(on_playback_error=self._on_playback_error)
        self._reconstructions_tab.set_on_add_to_sequencer(self._sequencer_tab.import_reconstruction)
        self._reconstructions_tab.set_can_add_to_sequencer(self._is_project_open)

    def _on_tab_changed(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        self._update_menu()

    def _build_initial_menu_state(self) -> MenuBarViewModel:
        return MenuBarViewModel(
            project_open=self.project_manager.is_open,
            reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
            reconstruction_saveable=self._reconstruction_coordinator.is_saveable(),
            reconstruction_in_project=self._editing_project_sample(),
            reconstruction_file_backed=self._reconstruction_coordinator.is_saveable(),
            reconstruction_audio_recorded=self.reconstruction_manager.audio_filepath is not None,
            can_undo=self.history.can_undo,
            can_redo=self.history.can_redo,
            play_label=self.language_manager[
                Page.GLOBAL,
                Panel.MENU,
                TextType.LABEL,
                MenuElements.ITEM_PLAYBACK_PLAY,
            ],
            play_or_pause_enabled=False,
            play_from_start_enabled=False,
            play_from_frame_enabled=False,
            pause_enabled=False,
            player_paused=False,
            stop_enabled=False,
            autoplay=self.session_manager.autoplay,
            follow_playback=self.session_manager.follow_playback,
            loop_song=self.session_manager.loop_song,
            fullscreen=self.session_manager.fullscreen,
            advanced_settings=self.session_manager.advanced_settings,
        )

    def _is_play_from_frame_enabled(self) -> bool:
        """Playing from the current frame applies to the Sequencer's song, so it needs that tab open."""
        return self._shell.get_current_tab() == Tab.SEQUENCER and self.project_manager.is_open

    def _build_menu_bar_viewmodel(self) -> MenuBarViewModel:
        return MenuBarViewModel(
            project_open=self.project_manager.is_open,
            reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
            reconstruction_saveable=self._reconstruction_coordinator.is_saveable(),
            reconstruction_in_project=self._editing_project_sample(),
            reconstruction_file_backed=self._reconstruction_coordinator.is_saveable(),
            reconstruction_audio_recorded=self.reconstruction_manager.audio_filepath is not None,
            can_undo=self.history.can_undo,
            can_redo=self.history.can_redo,
            play_label=self._playback_router.play_label,
            play_or_pause_enabled=self._playback_router.is_play_enabled,
            play_from_start_enabled=self._playback_router.is_play_from_start_enabled,
            play_from_frame_enabled=self._is_play_from_frame_enabled(),
            pause_enabled=self._playback_router.is_pause_enabled,
            player_paused=self._playback_router.is_paused,
            stop_enabled=self._playback_router.is_stop_enabled,
            autoplay=self.session_manager.autoplay,
            follow_playback=self.session_manager.follow_playback,
            loop_song=self.session_manager.loop_song,
            fullscreen=self.session_manager.fullscreen,
            advanced_settings=self.session_manager.advanced_settings,
        )

    def _on_history_changed(self) -> None:
        """Fans one history change out to every consumer.

        The manager exposes a single ``on_history_changed`` slot; the composition
        root owns it and forwards to the sequencer tab's history panel and the
        menu bar's undo/redo enablement, mirroring how session-state changes
        propagate.
        """
        self._sequencer_tab.refresh_history()
        self._update_menu()

    def _update_menu(self) -> None:
        self._shell.update_menu(self._build_menu_bar_viewmodel())

    def _toggle_autoplay(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self.session_manager.toggle_autoplay()
        self._update_menu()

    def _toggle_follow_playback(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self.session_manager.set_follow_playback(not self.session_manager.follow_playback)
        self._update_menu()

    def _toggle_loop_song(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self.session_manager.set_loop_song(not self.session_manager.loop_song)
        self._update_menu()

    def _toggle_advanced_settings(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self._main_tab.toggle_advanced_settings()
        self._update_menu()

    def _reconstruct_file_dialog(self) -> None:
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()

        filepath = open_file_dialog(
            title=self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.RECONSTRUCT_FILE,
            ],
            initial_directory=self.session_manager.get_audio_input_path(),
            extensions=EXT_FILES_AUDIO,
            filter_name=self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.FILTER,
                FileFilterElements.AUDIO,
            ],
        )

        self._handle_reconstruct_file(filepath)

    def _reconstruct_directory_dialog(self) -> None:
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()

        directory = select_directory_dialog(
            title=self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.RECONSTRUCT_DIRECTORY,
            ],
            initial_directory=self.session_manager.get_audio_input_path(),
        )

        self._handle_reconstruct_directory(directory)

    def _is_converter_panel_visible(self) -> bool:
        if self._main_tab is None:
            return False

        return self._main_tab.is_converter_panel_visible()

    def _is_operation_active(self) -> bool:
        return self._main_tab.is_converter_active() or self._instructions_tab.is_library_generating()

    def _refresh_busy_state(self) -> None:
        """Re-evaluate the reconstruct and generate-library buttons whenever a conversion or library
        generation starts or finishes, keeping the two long operations mutually exclusive. Each panel
        reads the live ``_is_operation_active`` state for itself; this only nudges them to
        re-apply, so the busy truth lives in one place."""
        self._instructions_tab.refresh_generate_button()

    def _on_library_operation_changed(self) -> None:
        """Responds to a library generation starting or finishing: refreshes the cross-tab action
        buttons and, additionally, the converter view so the Convert button reflects the library
        operation. The converter's own view changes refresh only the action buttons, so this extra
        converter refresh fires solely on library edges and stays clear of a refresh loop."""
        self._refresh_busy_state()
        self._main_tab.refresh_converter_view()

    def _export_reconstruction_wav_dialog(self) -> None:
        if self._reconstruction_coordinator.check_loaded():
            self._reconstructions_tab.request_export_wav_dialog()

    def _export_reconstruction_instruments_dialog(self) -> None:
        if self._reconstruction_coordinator.check_loaded():
            self._reconstructions_tab.request_export_instruments_dialog()

    def _reconstruct_file(self, filepath: Path) -> None:
        self._main_tab.set_input_path(filepath, convert=True)
        self.session_manager.set_audio_input_path(filepath.parent)
        self._set_current_tab(Tab.MAIN)
        self._update_menu()

    def _load_library(self, filepath: Path) -> None:
        self._instructions_tab.load_library_file(filepath)
        self.config_manager.update_gui()
        self._set_current_tab(Tab.INSTRUCTIONS)
        self._update_menu()

    @ignore_none_path
    def _handle_reconstruct_file(self, filepath: Path) -> None:
        self._reconstruct_file(filepath)

    def _reconstruct_directory(self, directory_path: Path) -> None:
        self._main_tab.set_input_path(directory_path, convert=True)
        self.session_manager.set_audio_input_path(directory_path)
        self._set_current_tab(Tab.MAIN)
        self._update_menu()

    @ignore_none_path
    def _handle_reconstruct_directory(self, directory_path: Path) -> None:
        self._reconstruct_directory(directory_path)

    def _on_playback_error(self, exception: Exception) -> None:
        logger.error_with_traceback(exception, "Playback error occurred")
        self.dialogs.show_error(
            exception,
            self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.MESSAGE,
                GlobalMessageElements.AUDIO_PLAYBACK_ERROR,
            ],
        )

    def _on_converted_reconstruction_loaded(self, filepath: Path) -> None:
        self._reconstruction_coordinator.load_with_confirmation(filepath)

    def _refresh_reconstruction_trees(self) -> None:
        self._reconstructions_tab.refresh_browser()
        self._sequencer_tab.refresh_browser()

    def _navigate_to_reconstructions(self) -> None:
        self._set_current_tab(Tab.RECONSTRUCTIONS)

    def _edit_project_sample(self, sample_id: str) -> None:
        sample = self.project_manager.current.sample(sample_id)
        if sample is None:
            logger.warning(f"Cannot edit unknown project sample: {sample_id}")
            return

        self.reconstruction_manager.load_reconstruction_object(
            sample.reconstruction,
            name=sample.name,
        )

    def _regenerate_instrument(
        self,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        feature_value: FeatureValue,
    ) -> None:
        self._reconstruction_coordinator.regenerate_instrument(
            generator_name,
            features,
            feature_key,
            feature_value,
        )

    def _on_reconstruction_updated(self, outcome: RegeneratedInstrument) -> None:
        """Records a reconstruction edit against the project when it owns the sample.

        Regeneration produces a fresh reconstruction. When the edited document is a
        project sample, the sample adopts the new reconstruction as one history
        entry labelled with the channel and feature ``outcome`` names; the
        copy-on-write swap keeps every prior snapshot's reconstruction intact. A
        standalone reconstruction leaves the project untouched. Consecutive edits
        of the same sample coalesce, so a continuous graph movement records a
        single entry.
        """
        sample = self._owning_project_sample()
        if sample is None:
            return

        with self.history.transaction(
            HistoryAction.EDIT_RECONSTRUCTION,
            detail=self._sequencer_tab.reconstruction_edit_detail(
                sample.id,
                outcome.generator_name,
                outcome.feature_key,
            ),
            coalesce=(sample.id,),
        ):
            self.project_controller.replace_sample_reconstruction(
                sample.id,
                outcome.reconstruction,
            )

    def _retune_samples_for_rate(self, nes_frequency: int) -> None:
        """Refreshes the stored reconstructions of samples left out of sync by a rate change.

        Song playback already follows the new rate; this re-synthesizes only the persistent
        rendered waveforms the Reconstructions tab edits, and only for the samples still off the
        target rate. The batch runs in the background so the rate change stays responsive.
        """
        targets = [
            (sample.id, sample.reconstruction)
            for sample in self.project_manager.current.samples
            if sample.reconstruction.config.nes_frequency != nes_frequency
        ]
        if not targets:
            return

        if not self.retune_service.start(targets, nes_frequency):
            return

        self.status_bar.set(
            self.language_manager[
                Page.GLOBAL,
                Panel.STATUS,
                TextType.MESSAGE,
                StatusElements.RETUNING_SAMPLES,
            ]
        )
        if self._editing_retuned_sample(nes_frequency):
            self._reconstructions_tab.set_reconstruction_dimmed(True)

    def _editing_retuned_sample(self, nes_frequency: int) -> bool:
        """Whether the open Reconstructions-tab document is a project sample this batch will retune."""
        sample = self._owning_project_sample()
        return sample is not None and sample.reconstruction.config.nes_frequency != nes_frequency

    def _on_retune_result(self, result: RetuneResult) -> None:
        match result:
            case ServiceSuccess(value=retuned):
                self._apply_retuned_sample(retuned)
            case ServiceError(exception=exception):
                logger.error_with_traceback(exception, "Sample retune failed")
            case ServiceCancelled():
                pass

        if not self.retune_service.is_running():
            self.status_bar.set("")
            self._reconstructions_tab.set_reconstruction_dimmed(False)

    def _apply_retuned_sample(self, retuned: RetunedSample) -> None:
        """Swaps a retuned reconstruction into its sample, folding it into the rate-change undo entry.

        A batch superseded by a newer rate change is discarded by the rate guard, so a stale
        result neither overwrites the current reconstruction nor appends a stray history entry. The
        rate-keyed coalesce target rewrites the single ``SET_NES_FREQUENCY`` entry, and a sample
        open in the Reconstructions tab rebinds so its editor and the project sample stay one object.
        """
        project = self.project_manager.current
        sample = project.samples.get(retuned.sample_id)
        if sample is None:
            return

        nes_frequency = retuned.reconstruction.config.nes_frequency
        if nes_frequency != project.settings.nes_frequency:
            return

        is_open = sample.reconstruction is self.reconstruction_manager.reconstruction
        with self.history.transaction(
            HistoryAction.SET_NES_FREQUENCY,
            detail=self._sequencer_tab.nes_frequency_detail(nes_frequency),
            coalesce=(nes_frequency,),
        ):
            self.project_controller.replace_sample_reconstruction(retuned.sample_id, retuned.reconstruction)

        if is_open:
            self.reconstruction_manager.apply_regenerated(retuned.reconstruction)
            self._reconstructions_tab.update_reconstruction()

    def _open_project_properties(self) -> None:
        """Opens the properties dialog seeded with the current project's info.

        The dialog receives a frozen snapshot, so its read path carries no
        controller reference; the edited values return through ``on_commit``.
        """
        if not self.project_controller.is_open:
            return

        info = self.project_controller.project.info
        self.project_properties_window.open(
            ProjectPropertiesViewModel(
                title=info.title,
                author=info.author,
                comment=info.comment,
                created=info.created,
                modified=info.modified,
            )
        )

    def _commit_project_properties(self, title: str, author: str, comment: str) -> None:
        """Applies the properties dialog's values as one undoable gesture.

        Only fields that differ from the current project info reach the controller,
        so confirming the dialog with no edits is a no-op.
        """
        info = self.project_controller.project.info
        with self.history.transaction(HistoryAction.EDIT_PROJECT_PROPERTIES):
            if title != info.title:
                self.project_controller.set_title(title)
            if author != info.author:
                self.project_controller.set_author(author)
            if comment != info.comment:
                self.project_controller.set_comment(comment)

    def _open_audio_settings(self) -> None:
        """Opens the audio settings dialog seeded with the device manager's state."""
        self.audio_settings_window.open(
            AudioSettingsViewModel.from_device_manager(
                self.audio_device_manager,
                master_gain=self.session_manager.master_gain,
            ),
        )

    def _open_about_dialog(self) -> None:
        """Presents the application name, version, description, and authorship in a modal notice."""
        description = self.language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.ABOUT_DESCRIPTION,
        ]
        author_line = self.language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.ABOUT_AUTHOR,
        ].format(
            author=SAMPLETONES_AUTHOR,
            group=SAMPLETONES_GROUP,
        )

        def content(parent: str) -> None:
            name_text = dpg.add_text(SAMPLETONES_NAME_VERSION, parent=parent)
            dpg.add_separator(parent=parent)
            FontRegistry.bind_to_item(name_text, Font.BOLD_LARGE)
            dpg.add_text(description, parent=parent, wrap=self.dialogs.default_wrap)
            author_text = dpg.add_text(author_line, parent=parent)
            FontRegistry.bind_to_item(author_text, Font.ITALIC)

        self.dialogs.show_modal(
            get_dialog_tag(TAG_GLOBAL_DIALOG_ABOUT),
            self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.ABOUT,
            ],
            content,
        )

    def _refresh_audio_devices(self) -> None:
        """Re-enumerates the output devices and repaints the open dialog in place."""
        self.audio_device_manager.refresh_devices()
        self.audio_settings_window.update_view(
            AudioSettingsViewModel.from_device_manager(
                self.audio_device_manager,
                master_gain=self.session_manager.master_gain,
            ),
        )

    def _apply_audio_settings(
        self,
        device_index: int,
        sample_rate: SampleRate,
        buffer_size: BufferSize,
    ) -> None:
        """Applies the dialog's committed device, sample rate, and buffer size."""
        self.audio_device_manager.configure_device(device_index, sample_rate)
        self.audio_device_manager.set_buffer_size(buffer_size)

    def _owning_project_sample(self) -> Optional[Sample]:
        reconstruction = self.reconstruction_manager.reconstruction
        if reconstruction is None:
            return None

        for sample in self.project_manager.current.samples:
            if sample.reconstruction is reconstruction:
                return sample

        return None

    def _editing_project_sample(self) -> bool:
        return self._owning_project_sample() is not None

    def _add_current_reconstruction_to_sequencer(self) -> None:
        reconstruction_data = self.reconstruction_manager.current_reconstruction
        if reconstruction_data is None or self._editing_project_sample():
            return

        self._sequencer_tab.import_reconstruction_object(
            reconstruction_data.reconstruction,
            reconstruction_data.name,
        )

    def _open_reconstruction_in_explorer(self) -> None:
        self._reconstructions_tab.open_reconstruction_in_explorer()

    def _locate_original_audio(self) -> None:
        self._reconstructions_tab.locate_original_audio()

    def _reconstruction_title_part(self) -> Optional[ReconstructionTitlePart]:
        reconstruction_name = self._reconstruction_coordinator.reconstruction_name
        if not self._reconstruction_coordinator.is_loaded() or reconstruction_name is None:
            return None

        unsaved_changes = self._reconstruction_coordinator.is_unsaved()
        sample = self._owning_project_sample()
        if sample is not None:
            ordinal = self.project_manager.current.samples.get_index(sample.id)
            name = SEQUENCER_SAMPLE_TITLE_FORMAT.format(
                ordinal=format(ordinal, SEQUENCER_SAMPLE_ORDINAL_FORMAT),
                name=sample.name,
            )
            return ReconstructionTitlePart(
                name=name,
                unsaved_changes=unsaved_changes,
                included=True,
            )

        return ReconstructionTitlePart(
            name=reconstruction_name,
            unsaved_changes=unsaved_changes,
            included=False,
        )

    def _update_title(self) -> None:
        untitled = self.language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.UNTITLED,
        ]
        document = document_title(
            self.project_manager.session,
            self._reconstruction_title_part(),
            untitled=untitled,
            project_open=self.project_manager.is_open,
        )
        application_name = self.language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            GlobalDialogTitleElements.MAIN_WINDOW,
        ]
        self._viewport_manager.update_title(window_title(application_name, document))

    def _sync_reconstruction_ownership(self) -> None:
        """Reflects sequencer ownership in the open reconstruction view.

        When the reconstruction on screen becomes a project sample — added to the sequencer — its
        source audio and file location are detached. The open document follows so both locations read
        as not applicable, matching an owned sample. The guard lets this run only when a file-backed
        reconstruction is added while it is the one on screen.
        """
        reconstruction_data = self.reconstruction_manager.current_reconstruction
        if reconstruction_data is None or reconstruction_data.filepath is None:
            return

        if self._owning_project_sample() is None:
            return

        self.reconstruction_manager.detach_current_reconstruction()
        self._reconstructions_tab.display_reconstruction()

    def _on_project_state_changed(self) -> None:
        self._sync_reconstruction_ownership()
        self._update_title()
        self._update_menu()

    def _on_reconstruction_state_changed(self) -> None:
        self._update_title()
        self._update_menu()

    def _set_current_tab(self, tab: Tab) -> None:
        self._shell.set_current_tab(tab)

    def _next_tab(self) -> None:
        self._switch_tab(1)

    def _previous_tab(self) -> None:
        self._switch_tab(-1)

    def _switch_tab(self, step: int) -> None:
        """Moves to the adjacent tab in declaration order, wrapping around at the ends."""
        tabs = list(Tab)
        index = tabs.index(self._shell.get_current_tab())
        self._set_current_tab(tabs[(index + step) % len(tabs)])

    def _get_active_source(self) -> Optional[AudioPlayerProtocol]:
        return self._shell.get_active_source()

    def _persist_application_state(self) -> None:
        self.session_manager.set_current_audio_device(self.audio_device_manager)
        self._viewport_manager.save_window_state()
        current_tab = self._shell.get_current_tab()
        self.session_manager.set_current_tab(current_tab)
        self.session_manager.save_config()

    def _play_from_start(self) -> None:
        self._playback_router.play_from_start()
        self._update_menu()

    def _play(self) -> None:
        self._playback_router.play()
        self._update_menu()

    def _play_from_frame(self) -> None:
        """Plays from the current order frame; available only in the Sequencer tab."""
        if self._shell.get_current_tab() != Tab.SEQUENCER:
            return

        self._sequencer_tab.play_from_current_frame()
        self._update_menu()

    def _stop(self) -> None:
        self._playback_router.stop()
        self._update_menu()

    def _show_confirmation_dialog(
        self,
        message: str,
        ok_label: str,
    ) -> None:
        self.dialogs.show_confirmation(
            tag=TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
            title=self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.EXIT_CONFIRMATION,
            ],
            message=message,
            on_confirm=self._exit_application,
            ok_label=ok_label,
        )

    def _on_close(self) -> None:
        if self.project_manager.is_dirty:
            self._project_coordinator.show_exit_save_confirmation(on_confirm=self._exit_application)

        elif self._reconstruction_coordinator.is_unsaved() and not self._editing_project_sample():
            self._reconstruction_coordinator.show_exit_save_confirmation(on_confirm=self._exit_application)

        elif self._is_converter_active():
            self._show_confirmation_dialog(
                self.language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.EXIT_CONVERSION_IN_PROGRESS,
                ],
                ok_label=self.language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.LABEL,
                    DialogElements.EXIT,
                ],
            )

        elif self._is_library_generating():
            self._show_confirmation_dialog(
                self.language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.EXIT_LIBRARY_GENERATION_IN_PROGRESS,
                ],
                ok_label=self.language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.LABEL,
                    DialogElements.EXIT,
                ],
            )

        else:
            self._exit_application()

    def _is_converter_active(self) -> bool:
        return self._main_tab.is_converter_active()

    def _is_library_generating(self) -> bool:
        return self._instructions_tab.is_library_generating()

    def _is_project_open(self) -> bool:
        return self.project_controller.is_open

    def _exit_application(self) -> None:
        stop_background_workers()
        self.audio_device_manager.stop()
        self._main_tab.cleanup()

        dpg.stop_dearpygui()

    def _update_status(self) -> None:
        delta_time = dpg.get_delta_time()
        self._shell.update_fps(delta_time)
        self._shell.update_status_bar(delta_time)
        self._refresh_playback_menu_state()

    def _refresh_playback_menu_state(self) -> None:
        """Keeps the playback menu entries in step with the output device.

        Tree previews drive the output device directly, so the menu learns about
        preview playback starting or finishing by sampling the device once per
        frame and refreshing when the playing state flips.
        """
        playing = self.audio_device_manager.is_playing()
        if playing == self._audio_was_playing:
            return

        self._audio_was_playing = playing
        self._update_menu()

    def frame(self) -> None:
        dpg.render_dearpygui_frame()

    def _post_frame(self) -> None:
        CaretOverlay.redraw()
        CallbackQueue.notify_frame()
        CallbackQueue.add(
            self._update_status,
            priority=self.layout.behavior.scheduling.priorities.update_status,
        )
        CallbackQueue.process(self.layout.behavior.scheduling.queue_budget_seconds)

    def _save_config(self) -> bool:
        try:
            self.config_manager.save_config()
            return False
        except OSError as exception:
            logger.error_with_traceback(exception, "Failed to save configuration on exit")
            return True

    def run(self) -> None:
        try:
            while dpg.is_dearpygui_running():
                self.frame()
                self._post_frame()
                self.frame_limiter.tick()
        except KeyboardInterrupt:
            return
        finally:
            stop_background_workers()
            self._main_tab.cleanup()
            self.library_manager.shutdown()
            save_failed = self._save_config()

            self._persist_application_state()
            self.audio_device_manager.terminate()
            dpg.destroy_context()
            if save_failed:
                raise SystemExit(1)
