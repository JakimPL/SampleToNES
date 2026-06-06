from pathlib import Path
from typing import Any, Optional

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
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.general import TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION
from sampletones_application.coordinators.config import ConfigCoordinator
from sampletones_application.coordinators.instructions import InstructionsTabCoordinator
from sampletones_application.coordinators.main import MainTabCoordinator
from sampletones_application.coordinators.playback import (
    AudioPlayerPanelProtocol,
    PlaybackRouter,
)
from sampletones_application.coordinators.project import ProjectCoordinator
from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.coordinators.reconstructions import ReconstructionsTabCoordinator
from sampletones_application.coordinators.sequencer import SequencerTabCoordinator
from sampletones_application.layout import LayoutConfig, load_layout_config
from sampletones_application.logic.instruction.library_manager import InstructionsLibraryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.project.title import document_title
from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.paths import BEHAVIOR_DIRECTORY, LANG_EN, LAYOUT_DIRECTORY
from sampletones_application.services import ConversionService, ExportService, RegenerationService
from sampletones_application.shell import ApplicationShell, ShortcutBindings
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.menu import MenuBar
from sampletones_application.ui.panels.settings import GUIAudioSettingsWindow
from sampletones_application.ui.themes.default import DefaultTheme
from sampletones_application.ui.themes.fps import FPSTimerTheme
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.file import file_dialog_handler
from sampletones_application.utils.fps import FPSTimer
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_application.viewport import ViewportManager
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.paths import EXT_FILES_AUDIO
from sampletones_core.types.feature import FeatureValue
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender


class Application:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.layout: LayoutConfig = load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY)
        self.language_manager: LanguageManager = LanguageManager(LANG_EN)
        self.dialogs: DialogsRenderer = DialogsRenderer(
            layout=self.layout.general,
            language_manager=self.language_manager,
        )
        setup_themes(self.layout)
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
        self.reconstruction_manager = ReconstructionManager(scheduling=self.layout.behavior.scheduling)

        _priority = self.layout.behavior.scheduling.priority_schedule
        self.conversion_service: ConversionService = ConversionService(priority=_priority)
        self.regeneration_service: RegenerationService = RegenerationService(priority=_priority)
        self.export_service: ExportService = ExportService(priority=_priority)

        self.project_manager: ProjectManager = ProjectManager()
        self.project_controller: ProjectController = ProjectController(self.project_manager)

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
            self.config_manager,
            self.audio_device_manager,
            dialogs=self.dialogs,
            language_manager=self.language_manager,
            layout=self.layout,
            on_tab_switch=self._set_current_tab,
            on_session_state_changed=self._on_reconstruction_state_changed,
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
            export_service=self.export_service,
            on_load_reconstruction_with_confirmation=self._reconstruction_coordinator.load_with_confirmation,
            on_reconstruction_loaded=self._reconstruction_coordinator._on_loaded,
            on_reconstruct_file=self._reconstruct_file_dialog,
            on_reconstruct_directory=self._reconstruct_directory_dialog,
            on_change_audio_state=self._update_menu,
            on_reconstruction_instrument_updated=self._regenerate_instrument,
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
            project_controller=self.project_controller,
            layout=self.layout,
            language_manager=self.language_manager,
            dialogs=self.dialogs,
        )
        self._sequencer_tab.on_edit_sample_requested = self._edit_project_sample

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
            self.session_manager,
            self.language_manager,
            self.shortcut_manager,
            self.layout,
            self.theme,
            self._viewport_manager,
            self._menu_bar,
            self.status_bar,
            self.fps_timer,
            self.audio_settings_window,
            main_tab=self._main_tab,
            reconstructions_tab=self._reconstructions_tab,
            sequencer_tab=self._sequencer_tab,
            instructions_tab=self._instructions_tab,
        )
        self._setup_gui()
        self._load_settings()

    def _load_settings(self) -> None:
        audio_device = self.session_manager.current_audio_device
        buffer_size = self.session_manager.current_buffer_size
        self.audio_device_manager.set_current_device(audio_device)
        self.audio_device_manager.set_buffer_size(buffer_size)

    def _setup_gui(self) -> None:
        bindings = ShortcutBindings(
            new_project=self._project_coordinator.new_project_with_confirmation,
            open_project=self._project_coordinator.open_with_confirmation,
            save_project=self._project_coordinator.save,
            save_project_as=self._project_coordinator.save_as_dialog,
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
        )
        self._shell.setup(
            bindings,
            on_close=self._on_close,
            on_tab_changed=self._on_tab_changed,
            initial_menu_state=self._build_initial_menu_state(),
        )
        self._set_callbacks()
        self._main_tab.emit_initial_view()
        self._sequencer_tab.initialize()
        self.config_manager.update_gui()
        self._update_menu()
        self._shell.restore_current_items(self.reconstruction_manager)

    def _set_callbacks(self) -> None:
        self.config_manager.add_config_change_callback(self._update_menu)
        self.audio_device_manager.set_callbacks(on_playback_error=self._on_playback_error)
        self._main_tab.converter_logic.on_load_file = self._on_converted_reconstruction_loaded
        self._main_tab.converter_logic.on_load_directory = self._reconstructions_tab.refresh_browser
        self._main_tab.converter_logic.on_cancelled = self._reconstructions_tab.refresh_browser
        self._main_tab.converter_logic.generate_library = self._instructions_tab.ensure_library_loaded

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
        if self._main_tab.is_converter_running():
            logger.warning("A conversion is already in progress; cannot start a new one")
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
        if self._main_tab.is_converter_running():
            logger.warning("A conversion is already in progress; cannot start a new one")
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

    def _is_generation_in_progress(self) -> bool:
        return self._main_tab.is_converter_running() or self._instructions_tab.is_library_generating()

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

        self.reconstruction_manager.load_reconstruction_object(sample.reconstruction)

    def _regenerate_instrument(
        self,
        generator_name: GeneratorName,
        features: Features,
        feature_key: FeatureKey,
        feature_value: FeatureValue,
    ) -> None:
        self._reconstruction_coordinator.regenerate_instrument(generator_name, features, feature_key, feature_value)
        if self._editing_project_sample():
            self.project_controller.mark_updated()

    def _editing_project_sample(self) -> bool:
        reconstruction = self.reconstruction_manager.reconstruction
        if reconstruction is None:
            return False

        return any(sample.reconstruction is reconstruction for sample in self.project_manager.current.samples)

    def _update_title(self) -> None:
        untitled = self.language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            DialogElements.UNTITLED,
        ]
        composed = document_title(
            self.project_manager.session,
            self._reconstruction_coordinator.reconstruction_session,
            untitled=untitled,
            project_open=self.project_manager.is_open,
            reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
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

    def _on_project_state_changed(self) -> None:
        self._update_title()
        self._update_menu()

    def _on_reconstruction_state_changed(self) -> None:
        self._update_title()
        self._update_menu()

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
        elif self._is_converter_running():
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

    def _is_converter_running(self) -> bool:
        return self._main_tab.is_converter_running()

    def _is_library_generating(self) -> bool:
        return self._instructions_tab.is_library_generating()

    def _exit_application(self) -> None:
        CallbackQueue.stop()
        self.audio_device_manager.stop()
        self._main_tab.converter_logic.cleanup()

        dpg.stop_dearpygui()

    def _update_status(self) -> None:
        delta_time = dpg.get_delta_time()
        self._shell.update_fps(delta_time)
        self._shell.update_status_bar(delta_time)

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
