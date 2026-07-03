from pathlib import Path
from typing import Any, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
    MenuElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.deployment import DeploymentConfig, load_deployment_config
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.general import (
    TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_MENU_FPS,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.coordinators.config import ConfigCoordinator
from sampletones_application.coordinators.instructions import InstructionsTabCoordinator
from sampletones_application.coordinators.main import MainTabCoordinator
from sampletones_application.coordinators.playback import (
    AudioPlayerPanelProtocol,
    PlaybackRouter,
)
from sampletones_application.coordinators.project import ProjectCoordinator
from sampletones_application.coordinators.reconstruction import (
    ReconstructionCoordinator,
)
from sampletones_application.coordinators.reconstructions import (
    ReconstructionsTabCoordinator,
)
from sampletones_application.coordinators.sequencer import SequencerTabCoordinator
from sampletones_application.layout import LayoutConfig, load_layout_config
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.project.title.document import ReconstructionTitlePart, document_title
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    DEPLOYMENT_CONFIG_PATH,
    LANG_EN,
    LAYOUT_DIRECTORY,
    THEME_DIRECTORY,
)
from sampletones_application.services import (
    ConversionService,
    ExportService,
    RegeneratedInstrument,
    RegenerationService,
)
from sampletones_application.shell import ApplicationShell, ShortcutBindings
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.table.caret import CaretOverlay
from sampletones_application.ui.menu import MenuBar
from sampletones_application.ui.panels.project_properties import GUIProjectPropertiesWindow
from sampletones_application.ui.panels.settings import GUIAudioSettingsWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.background import stop_background_workers
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.file import file_dialog_handler
from sampletones_application.utils.fps import FPSTimer
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.reconstruction.add_to_sequencer import AddToSequencerViewModel
from sampletones_application.view_model.sequencer.history import HistoryDetailRole, HistoryDetailSegment
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_application.viewport import ViewportManager
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.paths import EXT_FILES_AUDIO
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.types.feature import FeatureValue
from sampletones_core.utils.display import display_sample
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

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.deployment: DeploymentConfig = load_deployment_config(DEPLOYMENT_CONFIG_PATH)
        logger.set_level(self.deployment.log_level.to_logging_level())
        self.layout: LayoutConfig = load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY)
        self.language_manager: LanguageManager = LanguageManager(LANG_EN)
        self.dialogs: DialogsRenderer = DialogsRenderer(
            layout=self.layout.general,
            language_manager=self.language_manager,
        )
        FontRegistry.setup(self.layout.general.fonts)
        setup_themes(THEME_DIRECTORY)
        self.audio_device_manager: AudioDeviceManager = AudioDeviceManager()
        self.config_manager = ConfigManager(config_path)
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
        self.reconstruction_manager = ReconstructionManager(scheduling=self.layout.behavior.scheduling)

        _priority = self.layout.behavior.scheduling.priority_schedule
        self.conversion_service: ConversionService = ConversionService(priority=_priority)
        self.regeneration_service: RegenerationService = RegenerationService(priority=_priority)
        self.export_service: ExportService = ExportService(priority=_priority)

        self.project_manager: ProjectManager = ProjectManager()
        self.project_controller: ProjectController = ProjectController(self.project_manager)
        self.history: HistoryManager = HistoryManager(
            self.project_controller,
            budget=self.session_manager.history_budget,
            strict=self.deployment.strict_history,
        )
        self.project_controller.on_mutation = self.history.handle_mutation

        self.fps_timer: FPSTimer = FPSTimer()

        self.audio_settings_window: GUIAudioSettingsWindow = GUIAudioSettingsWindow(
            self.audio_device_manager,
            layout=self.layout.settings,
            language_manager=self.language_manager,
        )
        self.project_properties_window: GUIProjectPropertiesWindow = GUIProjectPropertiesWindow(
            self.project_controller,
            layout=self.layout.project_properties,
            language_manager=self.language_manager,
            shortcut_manager=self.shortcut_manager,
        )
        self.project_properties_window.on_commit = self._commit_project_properties
        self.status_bar = GUIStatusBar(
            display_time=self.layout.behavior.ui.status_bar_display_time,
        )
        self.theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT)
        self.fps_theme = ThemeRegistry.get(TAG_GLOBAL_THEME_MENU_FPS)

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

        self._project_coordinator = ProjectCoordinator(
            self.project_controller,
            self.project_manager,
            self.session_manager,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
            layout=self.layout,
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
            layout=self.layout,
            on_tab_switch=self._set_current_tab,
            on_session_state_changed=self._on_reconstruction_state_changed,
            on_reconstruction_updated=self._on_reconstruction_updated,
        )

        self._reconstructions_tab = ReconstructionsTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            reconstruction_manager=self.reconstruction_manager,
            browser_manager=self.browser_manager,
            export_service=self.export_service,
            on_load_reconstruction_with_confirmation=self._reconstruction_coordinator.load_with_confirmation,
            on_reconstruction_loaded=self._reconstruction_coordinator.on_reconstruction_loaded,
            on_reconstruct_file=self._reconstruct_file_dialog,
            on_reconstruct_directory=self._reconstruct_directory_dialog,
            on_change_audio_state=self._update_menu,
            on_reconstruction_instrument_updated=self._regenerate_instrument,
            is_operation_active=self._is_operation_active,
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
        )

        self._reconstruction_coordinator.set_reconstructions_tab(self._reconstructions_tab)

        self._instructions_tab = InstructionsTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            library_manager=self.library_manager,
            on_audio_state_changed=self._update_menu,
            on_generation_state_changed=self._on_library_operation_changed,
            is_operation_active=self._is_operation_active,
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
        )

        self._main_tab = MainTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            library_manager=self.library_manager,
            conversion_service=self.conversion_service,
            on_reconstruct_file=self._reconstruct_file,
            on_reconstruct_directory=self._reconstruct_directory,
            on_load_reconstruction=self._reconstruction_coordinator.load_with_confirmation,
            on_load_library=self._load_library,
            is_operation_active=self._is_operation_active,
            on_busy_state_changed=self._refresh_busy_state,
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
            on_load_file=self._on_converted_reconstruction_loaded,
            on_load_directory=self._reconstructions_tab.refresh_browser,
            on_cancelled=self._reconstructions_tab.refresh_browser,
            on_generate_library=self._instructions_tab.ensure_library_loaded,
        )

        self._sequencer_tab = SequencerTabCoordinator(
            config_manager=self.config_manager,
            session_manager=self.session_manager,
            audio_device_manager=self.audio_device_manager,
            shortcut_manager=self.shortcut_manager,
            browser_manager=self.browser_manager,
            project_controller=self.project_controller,
            history=self.history,
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
            on_edit_sample_requested=self._edit_project_sample,
            on_tab_switch=self._set_current_tab,
            on_export_module=self._project_coordinator.export_module_dialog,
            on_open_properties=self.project_properties_window.show,
        )

        self._playback_router = PlaybackRouter(
            current_player_fn=self._get_current_player,
            language_manager=self.language_manager,
        )

        self._config_coordinator = ConfigCoordinator(
            self.config_manager,
            self.session_manager,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
            layout=self.layout,
        )

        self._shell = ApplicationShell(
            session_manager=self.session_manager,
            language_manager=self.language_manager,
            shortcut_manager=self.shortcut_manager,
            layout=self.layout,
            theme=self.theme,
            viewport_manager=self._viewport_manager,
            menu_bar=self._menu_bar,
            status_bar=self.status_bar,
            fps_timer=self.fps_timer,
            audio_settings_window=self.audio_settings_window,
            project_properties_window=self.project_properties_window,
            main_tab=self._main_tab,
            reconstructions_tab=self._reconstructions_tab,
            sequencer_tab=self._sequencer_tab,
            instructions_tab=self._instructions_tab,
        )
        self._setup_gui()
        self._config_coordinator.present_pending_load_outcomes()
        self._load_settings()

    def _load_settings(self) -> None:
        audio_device = self.session_manager.current_audio_device
        buffer_size = self.session_manager.current_buffer_size
        self.audio_device_manager.set_current_device(audio_device)
        self.audio_device_manager.set_buffer_size(buffer_size)

    def _try_load_current_reconstruction(self, path: Path) -> None:
        self._reconstruction_coordinator.restore(path)

    def _try_load_current_project(self, path: Path) -> None:
        self._project_coordinator.restore(path)

    def _setup_gui(self) -> None:
        bindings = self._create_shortcut_bindings()
        self._setup_shell(bindings)
        self._initialize_caret()
        self._set_callbacks()
        self._main_tab.emit_initial_view()
        self._sequencer_tab.initialize()
        self.history.reset()
        self.config_manager.update_gui()
        self._update_menu()
        self._update_add_to_sequencer_state()
        self._restore_current_items()

    def _create_shortcut_bindings(self) -> ShortcutBindings:
        return ShortcutBindings(
            new_project=self._project_coordinator.new_project_with_confirmation,
            open_project=self._project_coordinator.open_with_confirmation,
            save_project=self._project_coordinator.save,
            save_project_as=self._project_coordinator.save_as_dialog,
            export_project_module=self._project_coordinator.export_module_dialog,
            project_properties=self._shell.open_project_properties,
            close_project=self._project_coordinator.close_with_confirmation,
            save_reconstruction=self._reconstruction_coordinator.save,
            save_reconstruction_as=self._reconstruction_coordinator.save_as_dialog,
            load_reconstruction=self._reconstruction_coordinator.load_with_confirmation,
            close_reconstruction=self._reconstruction_coordinator.close_with_confirmation,
            save_config=self._config_coordinator.save_dialog,
            load_config=self._config_coordinator.load_dialog,
            audio_settings=self._shell.open_audio_settings,
            exit=self._on_close,
            reconstruct_file=self._reconstruct_file_dialog,
            reconstruct_directory=self._reconstruct_directory_dialog,
            export_wav=self._export_reconstruction_wav_dialog,
            export_ftis=self._export_reconstruction_ftis_dialog,
            toggle_fullscreen=self._shell.toggle_fullscreen,
            toggle_advanced_settings=self._toggle_advanced_settings,
            play=self._play,
            play_from_start=self._play_from_start,
            stop=self._stop,
            toggle_autoplay=self._toggle_autoplay,
            undo=self._sequencer_tab.undo,
            redo=self._sequencer_tab.redo,
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

    def _restore_current_items(self) -> None:
        self._shell.restore_current_items(
            self._try_load_current_project,
            self._try_load_current_reconstruction,
        )

    def _set_callbacks(self) -> None:
        self.config_manager.add_config_change_callback(self._update_menu)
        self.audio_device_manager.set_callbacks(on_playback_error=self._on_playback_error)
        self._reconstructions_tab.set_on_add_to_sequencer(self._sequencer_tab.import_reconstruction)
        self._reconstructions_tab.set_can_add_to_sequencer(self._is_project_open)
        self._reconstructions_tab.set_on_add_current_reconstruction(self._add_current_reconstruction_to_sequencer)

    def _on_tab_changed(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        self._update_menu()

    def _build_initial_menu_state(self) -> MenuBarViewModel:
        return MenuBarViewModel(
            project_open=self.project_manager.is_open,
            reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
            play_label=self.language_manager[Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_PLAYBACK_PLAY],
            play_or_pause_enabled=False,
            stop_enabled=False,
            autoplay=self.session_manager.autoplay,
            fullscreen=self.session_manager.fullscreen,
            advanced_settings=self.session_manager.advanced_settings,
        )

    def _build_menu_bar_viewmodel(self) -> MenuBarViewModel:
        return MenuBarViewModel(
            project_open=self.project_manager.is_open,
            reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
            play_label=self._playback_router.play_label,
            play_or_pause_enabled=self._playback_router.is_play_enabled,
            stop_enabled=self._playback_router.is_stop_enabled,
            autoplay=self.session_manager.autoplay,
            fullscreen=self.session_manager.fullscreen,
            advanced_settings=self.session_manager.advanced_settings,
        )

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
        with dpg.file_dialog(
            label=self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.RECONSTRUCT_FILE,
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
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress; cannot start a new one")
            return

        self._instructions_tab.ensure_library_loaded()
        dpg.add_file_dialog(
            label=self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.RECONSTRUCT_DIRECTORY,
            ],
            width=self.layout.general.dialogs.file.width,
            height=self.layout.general.dialogs.file.height,
            callback=self._handle_reconstruct_directory,
            directory_selector=True,
            default_path=str(self.session_manager.get_reconstruction_path()),
            show=True,
        )

    def _is_operation_active(self) -> bool:
        return self._main_tab.is_converter_active() or self._instructions_tab.is_library_generating()

    def _refresh_busy_state(self) -> None:
        """Re-evaluate the reconstruct and generate-library buttons whenever a conversion or library
        generation starts or finishes, keeping the two long operations mutually exclusive. Each panel
        reads the live ``_is_operation_active`` state for itself; this only nudges them to
        re-apply, so the busy truth lives in one place."""
        self._reconstructions_tab.refresh_reconstruct_buttons()
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

    def _export_reconstruction_ftis_dialog(self) -> None:
        if self._reconstruction_coordinator.check_loaded():
            self._reconstructions_tab.request_export_instruments_dialog()

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
        self._reconstructions_tab.refresh_browser()
        self._reconstruction_coordinator.load_with_confirmation(filepath)

    def _edit_project_sample(self, sample_id: str) -> None:
        sample = self.project_manager.current.sample(sample_id)
        if sample is None:
            logger.warning(f"Cannot edit unknown project sample: {sample_id}")
            return

        self.reconstruction_manager.load_reconstruction_object(sample.reconstruction, name=sample.name)

    def _regenerate_instrument(
        self,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        feature_value: FeatureValue,
    ) -> None:
        self._reconstruction_coordinator.regenerate_instrument(generator_name, features, feature_key, feature_value)

    def _on_reconstruction_updated(self, outcome: RegeneratedInstrument) -> None:
        """Records a reconstruction edit against the project when it owns the sample.

        Regeneration produces a fresh reconstruction. When the edited document is a
        project sample, the sample adopts the new reconstruction as one history
        entry labelled with the channel and feature ``outcome`` names; the
        copy-on-write swap keeps every prior snapshot's reconstruction intact. A
        standalone reconstruction leaves the project untouched.
        """
        sample = self._owning_project_sample()
        if sample is None:
            return

        with self.history.transaction(
            HistoryAction.EDIT_RECONSTRUCTION,
            detail=self._reconstruction_detail(sample, outcome),
        ):
            self.project_controller.replace_sample_reconstruction(sample.id, outcome.reconstruction)

    def _reconstruction_detail(
        self,
        sample: Sample,
        outcome: RegeneratedInstrument,
    ) -> Tuple[HistoryDetailSegment, ...]:
        position = display_sample(samples=self.project_manager.current.samples, sample_id=sample.id)
        return (
            HistoryDetailSegment(text=f"{position}:", role=HistoryDetailRole.SAMPLE),
            HistoryDetailSegment(text=outcome.generator_name.capitalized, role=HistoryDetailRole.CHANNEL),
            HistoryDetailSegment(text=outcome.feature_key.capitalized, role=HistoryDetailRole.FEATURE),
        )

    def _commit_project_properties(self, title: str, author: str, comment: str) -> None:
        """Applies the properties dialog's values as one undoable gesture.

        Only fields that differ from the current project info reach the controller,
        so confirming the dialog with nothing edited leaves the history untouched.
        """
        info = self.project_controller.project.info
        with self.history.transaction(HistoryAction.EDIT_PROJECT_PROPERTIES):
            if title != info.title:
                self.project_controller.set_title(title)
            if author != info.author:
                self.project_controller.set_author(author)
            if comment != info.comment:
                self.project_controller.set_comment(comment)

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

    def _update_add_to_sequencer_state(self) -> None:
        self._reconstructions_tab.update_add_to_sequencer(
            AddToSequencerViewModel(
                reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
                project_open=self.project_controller.is_open,
                already_in_sequencer=self._editing_project_sample(),
            )
        )

    def _reconstruction_title_part(self) -> Optional[ReconstructionTitlePart]:
        session = self._reconstruction_coordinator.reconstruction_session
        if not session.is_loaded:
            return None

        sample = self._owning_project_sample()
        if sample is not None:
            ordinal = self.project_manager.current.samples.get_index(sample.id)
            name = SEQUENCER_SAMPLE_TITLE_FORMAT.format(
                ordinal=format(ordinal, SEQUENCER_SAMPLE_ORDINAL_FORMAT),
                name=sample.name,
            )
            return ReconstructionTitlePart(name=name, unsaved_changes=session.unsaved_changes, included=True)

        return ReconstructionTitlePart(name=session.name, unsaved_changes=session.unsaved_changes, included=False)

    def _update_title(self) -> None:
        untitled = self.language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.UNTITLED,
        ]
        composed = document_title(
            self.project_manager.session,
            self._reconstruction_title_part(),
            untitled=untitled,
            project_open=self.project_manager.is_open,
        )
        self._viewport_manager.update_title(
            self.language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.MAIN_WINDOW,
            ],
            composed,
        )

    def _sync_reconstruction_ownership(self) -> None:
        """Reflects sequencer ownership in the open reconstruction view.

        When the reconstruction on screen becomes a project sample — added to the sequencer — its
        source audio and file location are detached. The open document follows so both locations read
        as not applicable, matching an owned sample. The guard makes this a no-op except at the moment
        a file-backed reconstruction is added while it is the one on screen.
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
        self._update_add_to_sequencer_state()

    def _on_reconstruction_state_changed(self) -> None:
        self._update_title()
        self._update_menu()
        self._update_add_to_sequencer_state()

    def _set_current_tab(self, tab: Tab) -> None:
        self._shell.set_current_tab(tab)

    def _get_current_player(self) -> Optional[AudioPlayerPanelProtocol]:
        return self._shell.get_current_player()

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
        elif self._reconstruction_coordinator.is_unsaved():
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

    def frame(self) -> None:
        dpg.render_dearpygui_frame()

    def _post_frame(self) -> None:
        CaretOverlay.redraw()
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
            stop_background_workers()
            self._main_tab.cleanup()
            save_failed = False
            try:
                self.config_manager.save_config()
            except OSError as exception:
                logger.error_with_traceback(exception, "Failed to save configuration on exit")
                save_failed = True
            self._persist_application_state()
            self.audio_device_manager.terminate()
            dpg.destroy_context()
            if save_failed:
                raise SystemExit(1)
