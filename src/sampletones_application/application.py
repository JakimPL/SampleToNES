from pathlib import Path
from typing import Any, Dict, Final, Optional

import dearpygui.dearpygui as dpg
from pydantic import ValidationError

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.deployment.deployment import (
    DeploymentConfig,
)
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.constants.playback import FollowMode
from sampletones_application.coordinators.config import ConfigCoordinator
from sampletones_application.coordinators.display import DisplayCoordinator
from sampletones_application.coordinators.edit.router import EditRouter
from sampletones_application.coordinators.keybindings import KeybindingsCoordinator
from sampletones_application.coordinators.original_audio import OriginalAudioLocator
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.coordinators.playback.router import PlaybackRouter
from sampletones_application.coordinators.project import ProjectCoordinator
from sampletones_application.coordinators.reconstruction import (
    ReconstructionCoordinator,
)
from sampletones_application.coordinators.render import SongRenderCoordinator
from sampletones_application.coordinators.tabs.instructions import (
    InstructionsTabCoordinator,
)
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
from sampletones_application.logic.reconstruction.browser.manager import BrowserManager
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.render import SongRenderLogic
from sampletones_application.parameters import (
    InstructionsTabParameters,
    MainTabParameters,
    ReconstructionTabParameters,
    SequencerTabParameters,
)
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    DEPLOYMENT_CONFIG_PATH,
    KEYBINDINGS_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
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
    SongRenderService,
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
from sampletones_application.ui.panels.dialogs.countdown import GUICountdownWindow
from sampletones_application.ui.panels.dialogs.display_settings import (
    GUIDisplaySettingsWindow,
)
from sampletones_application.ui.panels.dialogs.keybindings import GUIKeybindingsWindow
from sampletones_application.ui.panels.dialogs.project_properties import (
    GUIProjectPropertiesWindow,
)
from sampletones_application.ui.panels.dialogs.render import GUIRenderWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.file_dialogs.api import (
    open_file_dialog,
    select_directory_dialog,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.fps import FPSTimer
from sampletones_application.utils.frame_limiter import FrameLimiter
from sampletones_application.utils.gui.dialogs import DialogsRenderer, get_dialog_tag
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.palette.palette import PaletteBindings
from sampletones_application.utils.gui.shortcuts.catalog import ShortcutCatalog
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.source import PaletteSource
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
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures.tree import FileSystemNode
from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.registry import build_tracker_backends
from sampletones_core.types.feature import FeatureValue
from sampletones_shared.application import (
    SAMPLETONES_AUTHOR,
    SAMPLETONES_GROUP,
    SAMPLETONES_NAME_VERSION,
)
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.logger import logger
from sampletones_shared.paths.extensions import EXT_FILES_AUDIO
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
        profile: UserProfile,
        config_path: Optional[Path] = None,
        library_path: Optional[Path] = None,
        reconstruction_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
    ) -> None:
        self.deployment: DeploymentConfig = DeploymentConfig.load(DEPLOYMENT_CONFIG_PATH)
        self._set_logging_level()

        self.session_manager = SessionManager(profile)
        self._palette_catalog: PaletteCatalog = PaletteCatalog.load(PALETTES_DIRECTORY)
        self._palette_source: PaletteSource = PaletteSource(
            self._palette_catalog.select(self.session_manager.palette_name),
        )
        self.layout: LayoutConfig = self._load_layout_config()
        self._setup_gui_elements()

        self.language_manager: LanguageManager = LanguageManager(LANG_EN)

        self.status_bar = GUIStatusBar(
            display_time=self.layout.behavior.ui.status_bar_display_time,
        )
        self.key_router: KeyRouter = KeyRouter()
        self._shortcut_catalog: ShortcutCatalog = ShortcutCatalog.load(KEYBINDINGS_DIRECTORY)
        self._shortcut_source: ShortcutSource = ShortcutSource(self._preferred_scheme())
        self.shortcut_manager: ShortcutManager = ShortcutManager(
            key_router=self.key_router,
            shortcut_source=self._shortcut_source,
        )
        self.dialogs: DialogsRenderer = DialogsRenderer(
            layout=self.layout.general,
            language_manager=self.language_manager,
            status_bar=self.status_bar,
            key_router=self.key_router,
            shortcut_source=self._shortcut_source,
        )
        self.audio_device_manager: AudioDeviceManager = AudioDeviceManager()
        self.config_manager = ConfigManager(config_path)

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
        self.render_service: SongRenderService = SongRenderService(priority=_priority)
        self.retune_service: SampleRetuneService = SampleRetuneService(priority=_priority)
        self.retune_service.subscribe(self._on_retune_result)

        self.tracker_backends: Dict[TrackerFormat, TrackerBackend] = build_tracker_backends()

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

        self.fps_timer: FPSTimer = FPSTimer(interval=self.layout.behavior.ui.fps_update_interval)
        self.frame_limiter: FrameLimiter = FrameLimiter(self.session_manager.max_fps)
        self._audio_was_playing: bool = False

        self.audio_settings_window: GUIAudioSettingsWindow = GUIAudioSettingsWindow(
            layout=self.layout.settings,
            language_manager=self.language_manager,
            key_router=self.key_router,
            shortcut_source=self._shortcut_source,
        )
        self.audio_settings_window.on_commit = self._apply_audio_settings
        self.audio_settings_window.on_refresh_devices = self._refresh_audio_devices
        self.audio_settings_window.on_master_gain_changed = self.session_manager.set_master_gain
        self.display_settings_window: GUIDisplaySettingsWindow = GUIDisplaySettingsWindow(
            layout=self.layout.settings,
            language_manager=self.language_manager,
            key_router=self.key_router,
            shortcut_source=self._shortcut_source,
        )
        self.keybindings_window: GUIKeybindingsWindow = GUIKeybindingsWindow(
            layout=self.layout.settings,
            language_manager=self.language_manager,
            key_router=self.key_router,
            shortcut_source=self._shortcut_source,
        )
        self.display_countdown_window: GUICountdownWindow = GUICountdownWindow(
            layout=self.layout.settings.display.countdown,
            title=self.language_manager["settings.display.title.countdown"],
            message=self.language_manager["settings.display.message.countdown"],
            remaining_format=self.language_manager["settings.display.template.countdown_remaining"],
            keep_label=self.language_manager["settings.display.label.keep_button"],
            revert_label=self.language_manager["settings.display.label.revert_button"],
            key_router=self.key_router,
            shortcut_source=self._shortcut_source,
        )
        self.render_window: GUIRenderWindow = GUIRenderWindow(
            layout=self.layout.settings,
            path_colors=self.layout.general.colors.paths,
            language_manager=self.language_manager,
            key_router=self.key_router,
            shortcut_source=self._shortcut_source,
            status_bar=self.status_bar,
        )
        self.project_properties_window: GUIProjectPropertiesWindow = GUIProjectPropertiesWindow(
            layout=self.layout.project_properties,
            language_manager=self.language_manager,
            key_router=self.key_router,
            shortcut_source=self._shortcut_source,
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
            build_edit_actions=self._build_edit_actions,
            on_play_from_start=self._play_from_start,
            on_pause_or_resume=self._play,
            on_stop=self._stop,
            on_channel_muted=self._mute_channel,
        )

        self._viewport_manager = ViewportManager(
            self.session_manager,
            self.theme,
            self.layout.general.window,
            on_fullscreen_state_changed=self._update_menu,
        )

        self._display_coordinator = DisplayCoordinator(
            self.session_manager,
            self._viewport_manager,
            self.frame_limiter,
            self._palette_source,
            self._palette_catalog,
            window=self.display_settings_window,
            countdown=self.display_countdown_window,
            behavior=self.layout.behavior.display,
            window_layout=self.layout.general.window,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
        )

        self._keybindings_coordinator = KeybindingsCoordinator(
            self.session_manager,
            self._shortcut_source,
            self._shortcut_catalog,
            window=self.keybindings_window,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
        )

        self._project_coordinator = ProjectCoordinator(
            self.project_controller,
            self.project_manager,
            self.session_manager,
            self.export_service,
            tracker_backends=self.tracker_backends,
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
            tracker_backends=self.tracker_backends,
            on_load_reconstruction_with_confirmation=self._reconstruction_coordinator.load_with_confirmation,
            on_change_audio_state=self._update_menu,
            on_favorite_changed=self._repaint_reconstruction_favorites,
            on_reconstruction_instrument_updated=self._regenerate_instrument,
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
            shortcut_source=self._shortcut_source,
            browser_manager=self.browser_manager,
            project_controller=self.project_controller,
            history=self.history,
            original_audio_locator=self._original_audio_locator,
            tab_active=self._is_sequencer_tab_current,
            layout=SequencerTabParameters.from_config(self.layout),
            language_manager=self.language_manager,
            dialogs=self.dialogs,
            status_bar=self.status_bar,
            on_edit_sample_requested=self._edit_project_sample,
            on_favorite_changed=self._repaint_reconstruction_favorites,
            on_sample_reconstruction_replaced=self._rebind_replaced_sample,
            on_tab_switch=self._set_current_tab,
            on_nes_frequency_changed=self._retune_samples_for_rate,
            on_channels_changed=self._update_menu,
        )

        self._edit_router = EditRouter(surfaces=self._sequencer_tab.edit_surfaces)

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

        self._render_logic = SongRenderLogic(
            self.project_controller,
            self.config_manager,
            self.session_manager,
            self.render_service,
            language_manager=self.language_manager,
            is_operation_active=self._is_operation_active,
        )

        self._render_coordinator = SongRenderCoordinator(
            self._render_logic,
            window=self.render_window,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
            on_activity_changed=self._on_render_activity_changed,
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
            return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, self._palette_source)
        except ValidationError as exception:
            raise SystemError(f"Invalid layout configuration: {exception}") from exception

    def _preferred_scheme(self) -> ShortcutScheme:
        """The keys the session runs under: the scheme it names, as its own overrides rebind it."""
        scheme = self._shortcut_catalog.select(self.session_manager.shortcut_scheme_name)
        return scheme.with_overrides(self.session_manager.shortcut_overrides)

    def _setup_gui_elements(self) -> None:
        FontRegistry.setup(self.layout.fonts)
        GUIPanel.configure_section_header(
            self.layout.glyphs,
            self.layout.general.section_header,
            self.layout.general.collapse,
        )

        try:
            setup_themes(THEME_DIRECTORY, self._palette_source)
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
            export_project=self._project_coordinator.export_project_dialog,
            render_song=self._render_coordinator.open,
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
            set_follow_mode=self._set_follow_mode,
            toggle_loop_song=self._toggle_loop_song,
            toggle_channel=self._toggle_channel,
            unmute_all_channels=self._sequencer_tab.unmute_all_channels,
            audio_settings=self._open_audio_settings,
            display_settings=self._display_coordinator.open,
            keyboard_settings=self._keybindings_coordinator.open,
            toggle_advanced_settings=self._toggle_advanced_settings,
            toggle_fullscreen=self._shell.toggle_fullscreen,
            about=self._open_about_dialog,
            next_tab=self._next_tab,
            previous_tab=self._previous_tab,
            select_tab=self._set_current_tab,
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
        self._palette_source.on_palette_changed = self._on_palette_changed
        self._shortcut_source.on_bindings_changed = self._on_bindings_changed

    def _on_bindings_changed(self, _scheme: ShortcutScheme) -> None:
        """Hands the keys of the scheme now in place to what has already read a combination.

        Every registration names the action it fires, so the work left is the copies of the keys:
        the index a press resolves through and the accelerators the menus print.
        """
        self.shortcut_manager.rebind()

    def _on_palette_changed(self, _palette: Palette) -> None:
        """Repaints what holds a colour DearPyGui has copied, once another palette is in place.

        Every layout and theme colour already answers with the new palette, so the work left is
        handing those values to the copies DearPyGui keeps: the registered theme colours and item
        arguments, the viewport clear colour, and the sequencer tables, whose tints belong to the
        table rather than to an item.
        """
        PaletteBindings.apply()
        self._viewport_manager.refresh_clear_color()
        self._sequencer_tab.repaint()

    def _on_tab_changed(
        self,
        _sender: Sender,
        _app_data: Any,
        _user_data: Any,
    ) -> None:
        self._update_menu()

    def _build_initial_menu_state(self) -> MenuBarViewModel:
        return MenuBarViewModel(
            project_open=self.project_manager.is_open,
            reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
            reconstruction_saveable=self._reconstruction_coordinator.is_saveable(),
            reconstruction_in_project=self._editing_project_sample(),
            reconstruction_file_backed=self._reconstruction_coordinator.is_saveable(),
            reconstruction_audio_recorded=self.reconstruction_manager.audio_filepath is not None,
            operation_active=self._is_operation_active(),
            can_undo=self.history.can_undo,
            can_redo=self.history.can_redo,
            play_label=self.language_manager["global.menu.label.item_playback_play"],
            play_or_pause_enabled=False,
            play_from_start_enabled=False,
            play_from_frame_enabled=False,
            pause_enabled=False,
            player_paused=False,
            stop_enabled=False,
            autoplay=self.session_manager.autoplay,
            follow_mode=self.session_manager.follow_mode,
            loop_song=self.session_manager.loop_song,
            channels=self._sequencer_tab.channels,
            fullscreen=self.session_manager.fullscreen,
            advanced_settings=self.session_manager.advanced_settings,
        )

    def _is_sequencer_tab_current(self) -> bool:
        """Whether the Sequencer is the tab in front, which is what puts its panels on the keyboard.

        The tracker, order and samples panels keep their cursor and selection while another tab is
        worked on, so this is what tells a press meant for the reconstruction in front from one
        meant for the song.
        """
        return self._shell.get_current_tab() == Tab.SEQUENCER

    def _is_play_from_frame_enabled(self) -> bool:
        """Playing from the current frame applies to the Sequencer's song, so it needs that tab open."""
        return self._is_sequencer_tab_current() and self.project_manager.is_open

    def _build_menu_bar_viewmodel(self) -> MenuBarViewModel:
        return MenuBarViewModel(
            project_open=self.project_manager.is_open,
            reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
            reconstruction_saveable=self._reconstruction_coordinator.is_saveable(),
            reconstruction_in_project=self._editing_project_sample(),
            reconstruction_file_backed=self._reconstruction_coordinator.is_saveable(),
            reconstruction_audio_recorded=self.reconstruction_manager.audio_filepath is not None,
            operation_active=self._is_operation_active(),
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
            follow_mode=self.session_manager.follow_mode,
            loop_song=self.session_manager.loop_song,
            channels=self._sequencer_tab.channels,
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
        _sender: Optional[Sender] = None,
        _app_data: Optional[Any] = None,
        _user_data: Optional[Any] = None,
    ) -> None:
        self.session_manager.toggle_autoplay()
        self._update_menu()

    def _set_follow_mode(self, mode: FollowMode) -> None:
        """Chooses how far the sequencer view chases the playhead, and marks the choice in the menu.

        The tab coordinator carries this to the player, which holds the setting and emits a view as
        it changes, so the grid's following settles in the same step as the menu's mark.
        """
        self._sequencer_tab.set_follow_mode(mode)
        self._update_menu()

    def _toggle_loop_song(
        self,
        _sender: Optional[Sender] = None,
        _app_data: Optional[Any] = None,
        _user_data: Optional[Any] = None,
    ) -> None:
        self.session_manager.set_loop_song(not self.session_manager.loop_song)
        self._update_menu()

    def _toggle_advanced_settings(
        self,
        _sender: Optional[Sender] = None,
        _app_data: Optional[Any] = None,
        _user_data: Optional[Any] = None,
    ) -> None:
        self._main_tab.toggle_advanced_settings()
        self._update_menu()

    def _reconstruct_file_dialog(self) -> None:
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()

        filepath = open_file_dialog(
            title=self.language_manager["global.dialog.title.reconstruct_file"],
            initial_directory=self.session_manager.get_audio_input_path(),
            filters=(
                FileFilter.for_extensions(
                    self.language_manager["global.dialog.filter.audio"],
                    EXT_FILES_AUDIO,
                ),
            ),
        )

        self._handle_reconstruct_file(filepath)

    def _reconstruct_directory_dialog(self) -> None:
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()

        directory = select_directory_dialog(
            title=self.language_manager["global.dialog.title.reconstruct_directory"],
            initial_directory=self.session_manager.get_audio_input_path(),
        )

        self._handle_reconstruct_directory(directory)

    def _is_converter_panel_visible(self) -> bool:
        if self._main_tab is None:
            return False

        return self._main_tab.is_converter_panel_visible()

    def _is_operation_active(self) -> bool:
        return (
            self._main_tab.is_converter_active()
            or self._instructions_tab.is_library_generating()
            or self._render_coordinator.is_active
        )

    def _refresh_busy_state(self) -> None:
        """Re-evaluate the reconstruct and generate-library buttons whenever a conversion, library
        generation or render starts or finishes, keeping the long operations mutually exclusive. Each
        panel reads the live ``_is_operation_active`` state for itself; this only nudges them to
        re-apply, so the busy truth lives in one place. The menu follows the same edge, since what
        greys an entry offering another such operation is one already running."""
        self._instructions_tab.refresh_generate_button()
        self._update_menu()

    def _on_render_activity_changed(self) -> None:
        """Follows a render claiming the application and handing it back.

        What a render occupies is the same ground a conversion or a library generation occupies,
        so its edges reach the same busy state — the action buttons of each tab, the converter's
        own view, and the menu entries that would start another exclusive operation.
        """
        self._refresh_busy_state()
        self._main_tab.refresh_converter_view()

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

    def _export_reconstruction_instruments_dialog(self, tracker_format: TrackerFormat) -> None:
        if self._reconstruction_coordinator.check_loaded():
            self._reconstructions_tab.request_export_instruments_dialog(tracker_format)

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
            self.language_manager["global.dialog.message.audio_playback_error"],
        )

    def _on_converted_reconstruction_loaded(self, filepath: Path) -> None:
        self._reconstruction_coordinator.load_with_confirmation(filepath)

    def _refresh_reconstruction_trees(self) -> None:
        self._reconstructions_tab.refresh_browser()
        self._sequencer_tab.refresh_browser()

    def _repaint_reconstruction_favorites(self, node: FileSystemNode) -> None:
        """Repaints the toggled path in both browsers, whichever tab the star was clicked in.

        The two browsers render one tree and read one set of favorites, so the rows standing for the
        toggled path are read once here and handed to each of them.
        """
        nodes = self.browser_manager.nodes_at(node.filepath)
        self._reconstructions_tab.repaint_browser_favorites(nodes)
        self._sequencer_tab.repaint_browser_favorites(nodes)

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

    def _rebind_replaced_sample(
        self,
        sample_id: str,
        reconstruction: Reconstruction,
    ) -> None:
        """Points the open Reconstructions-tab document at the reconstruction replacing the one it edits.

        The editor and its owning sample share one reconstruction object, so a sample whose audio is
        substituted takes its editor along. This runs while the sample still holds the outgoing
        reconstruction, which is what identifies the open document as belonging to it.

        Args:
            sample_id: The sample receiving a new reconstruction.
            reconstruction: The reconstruction the sample is about to hold.
        """
        sample = self.project_manager.current.sample(sample_id)
        if sample is None or sample.reconstruction is not self.reconstruction_manager.reconstruction:
            return

        self.reconstruction_manager.apply_regenerated(reconstruction)
        self._reconstructions_tab.update_reconstruction()

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

    def _on_reconstruction_updated(
        self,
        outcome: RegeneratedInstrument,
    ) -> None:
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

        self.status_bar.set(self.language_manager["global.status.message.retuning_samples"])
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
            self.project_controller.replace_sample_reconstruction(
                retuned.sample_id,
                retuned.reconstruction,
            )

        if is_open:
            self.reconstruction_manager.apply_regenerated(
                retuned.reconstruction,
            )
            self._reconstructions_tab.update_reconstruction()

    def _open_project_properties(self) -> None:
        """Opens the properties dialog seeded with the current project's info.

        The dialog receives a frozen snapshot, so its read path carries no
        controller reference; the edited values return through ``on_commit``.
        """
        if not self.project_controller.is_open:
            return

        info = self.project_controller.project.info
        settings = self.project_controller.project.settings
        self.project_properties_window.open(
            ProjectPropertiesViewModel(
                title=info.title,
                author=info.author,
                comment=info.comment,
                first_highlight=settings.first_highlight,
                second_highlight=settings.second_highlight,
                created=info.created,
                modified=info.modified,
            )
        )

    def _commit_project_properties(
        self,
        title: str,
        author: str,
        comment: str,
        first_highlight: int,
        second_highlight: int,
    ) -> None:
        """Applies the properties dialog's values as one undoable gesture.

        Only fields that differ from the current project reach the controller, so
        confirming the dialog with no edits is a no-op.
        """
        info = self.project_controller.project.info
        settings = self.project_controller.project.settings
        with self.history.transaction(HistoryAction.EDIT_PROJECT_PROPERTIES):
            if title != info.title:
                self.project_controller.set_title(title)
            if author != info.author:
                self.project_controller.set_author(author)
            if comment != info.comment:
                self.project_controller.set_comment(comment)
            if first_highlight != settings.first_highlight:
                self.project_controller.set_first_highlight(first_highlight)
            if second_highlight != settings.second_highlight:
                self.project_controller.set_second_highlight(second_highlight)

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
        description = self.language_manager["global.dialog.message.about_description"]
        author_line = self.language_manager["global.dialog.template.about_author"].format(
            author=SAMPLETONES_AUTHOR,
            group=SAMPLETONES_GROUP,
        )

        def content(parent: str) -> None:
            name_text = dpg.add_text(SAMPLETONES_NAME_VERSION, parent=parent)
            dpg.add_separator(parent=parent)
            FontRegistry.bind_to_item(name_text, Font.BOLD_LARGE)
            dpg.add_text(
                description,
                parent=parent,
                wrap=self.dialogs.default_wrap,
            )
            author_text = dpg.add_text(author_line, parent=parent)
            FontRegistry.bind_to_item(author_text, Font.ITALIC)

        self.dialogs.show_modal(
            get_dialog_tag(TAG_GLOBAL_DIALOG_ABOUT),
            self.language_manager["global.dialog.title.about"],
            content,
        )

    def _refresh_audio_devices(self) -> None:
        """Re-enumerates the output devices and repaints the open dialog in place.

        Re-enumeration restarts the audio backend, which needs the output free; a source that
        keeps hold of it leaves the device list as it stands and reports the failure.
        """
        try:
            self.audio_device_manager.refresh_devices()
        except PlaybackError as exception:
            self._on_playback_error(exception)
            return

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
        """Applies the dialog's committed device, sample rate, and buffer size.

        Switching devices needs the output free; a source that keeps hold of it leaves the
        settings as they stand and reports the failure.
        """
        try:
            self.audio_device_manager.configure_device(device_index, sample_rate)
        except PlaybackError as exception:
            self._on_playback_error(exception)
            return

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
        untitled = self.language_manager["global.dialog.label.untitled"]
        document = document_title(
            self.project_manager.session,
            self._reconstruction_title_part(),
            untitled=untitled,
            project_open=self.project_manager.is_open,
        )
        application_name = self.language_manager["global.dialog.title.main_window"]
        self._viewport_manager.update_title(
            window_title(
                application_name,
                document,
            )
        )

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

    def _build_edit_actions(self) -> bool:
        """States the actions of the grid holding the cursor into the Edit menu being built."""
        return self._edit_router.build_menu_actions()

    def _play_from_start(self) -> None:
        self._playback_router.play_from_start()
        self._update_menu()

    def _play(self) -> None:
        self._playback_router.play()
        self._update_menu()

    def _play_from_frame(self) -> None:
        """Plays from the current order frame; available only in the Sequencer tab."""
        if not self._is_sequencer_tab_current():
            return

        self._sequencer_tab.play_from_current_frame()
        self._update_menu()

    def _stop(self) -> None:
        self._playback_router.stop()
        self._update_menu()

    def _toggle_channel(self, generator: GeneratorName) -> None:
        """Switches one NES channel in the tab in front of the reader.

        A channel is switched by a control of its own on three tabs: the generators a
        reconstruction is built from on the Main tab, the slices the waveform draws and plays on
        the Reconstructions tab, and the sequencer's mix elsewhere. One key reaches whichever of
        them is on screen, so a reader silences what they are listening to without leaving it.
        """
        match self._shell.get_current_tab():
            case Tab.MAIN:
                self._main_tab.toggle_generator(generator)
            case Tab.RECONSTRUCTIONS:
                self._reconstructions_tab.toggle_generator(generator)
            case _:
                self._mute_channel(generator)

    def _mute_channel(self, generator: GeneratorName) -> None:
        """Flips one channel of the sequencer's mix, the gesture the Channels submenu offers."""
        self._sequencer_tab.toggle_channel(generator)

    def _show_confirmation_dialog(
        self,
        message: str,
        ok_label: str,
    ) -> None:
        self.dialogs.show_confirmation(
            tag=TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
            title=self.language_manager["global.dialog.title.exit_confirmation"],
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
                self.language_manager["global.dialog.message.exit_conversion_in_progress"],
                ok_label=self.language_manager["global.dialog.label.exit"],
            )

        elif self._is_library_generating():
            self._show_confirmation_dialog(
                self.language_manager["global.dialog.message.exit_library_generation_in_progress"],
                ok_label=self.language_manager["global.dialog.label.exit"],
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
        self._render_coordinator.cleanup()
        stop_background_workers()
        self._playback_router.shutdown()
        self._main_tab.cleanup()

        dpg.stop_dearpygui()

    def _update_status(self) -> None:
        delta_time = dpg.get_delta_time()
        self._shell.update_fps(delta_time)
        self._shell.update_status_bar(delta_time)
        self._display_coordinator.tick(delta_time)
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
            self._render_coordinator.cleanup()
            stop_background_workers()
            self._playback_router.shutdown()
            self._main_tab.cleanup()
            self.library_manager.shutdown()
            save_failed = self._save_config()

            self._persist_application_state()
            self.audio_device_manager.terminate()
            dpg.destroy_context()
            if save_failed:
                raise SystemExit(1)
