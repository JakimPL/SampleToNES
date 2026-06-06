from dataclasses import dataclass
from typing import Any, Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import GlobalDialogTitleElements
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.general import (
    TAG_GLOBAL_STATUS_WINDOW,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
    TAG_GLOBAL_TAB_MAIN,
    TAG_GLOBAL_TAB_RECONSTRUCTIONS,
    TAG_GLOBAL_TAB_SEQUENCER,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.coordinators.instructions import InstructionsTabCoordinator
from sampletones_application.coordinators.main import MainTabCoordinator
from sampletones_application.coordinators.playback import AudioPlayerPanelProtocol, PlaybackRouter
from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.coordinators.reconstructions import ReconstructionsTabCoordinator
from sampletones_application.coordinators.sequencer import SequencerTabCoordinator
from sampletones_application.layout import LayoutConfig
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.menu import MenuBar
from sampletones_application.ui.panels.settings import GUIAudioSettingsWindow
from sampletones_application.ui.themes.default import DefaultTheme
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.fps import FPSTimer
from sampletones_application.utils.shortcuts.ids import ShortcutId
from sampletones_application.utils.shortcuts.keys import Modifier
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.utils.shortcuts.shortcut import Shortcut
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_application.viewport import ViewportManager
from sampletones_shared.exceptions import LoadReconstructionError
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback

_TAB_TAGS: Dict[Tab, str] = {
    Tab.MAIN: TAG_GLOBAL_TAB_MAIN,
    Tab.RECONSTRUCTIONS: TAG_GLOBAL_TAB_RECONSTRUCTIONS,
    Tab.SEQUENCER: TAG_GLOBAL_TAB_SEQUENCER,
    Tab.INSTRUCTIONS: TAG_GLOBAL_TAB_INSTRUCTIONS,
}
_TAG_TABS: Dict[str, Tab] = {tag: Tab(tab) for tab, tag in _TAB_TAGS.items()}


@dataclass(frozen=True)
class ShortcutBindings:
    new_project: Callback
    open_project: Callback
    save_project: Callback
    save_project_as: Callback
    close_project: Callback
    save_reconstruction: Callback
    save_reconstruction_as: Callback
    load_reconstruction: Callback
    close_reconstruction: Callback
    save_config: Callback
    load_config: Callback
    audio_settings: Callback
    exit: Callback
    reconstruct_file: Callback
    reconstruct_directory: Callback
    export_wav: Callback
    export_ftis: Callback
    toggle_fullscreen: Callback
    toggle_advanced_settings: Callback
    play: Callback
    play_from_start: Callback
    stop: Callback
    toggle_autoplay: Callback


class ApplicationShell:
    def __init__(
        self,
        session_manager: SessionManager,
        language_manager: LanguageManager,
        shortcut_manager: ShortcutManager,
        layout: LayoutConfig,
        theme: DefaultTheme,
        viewport_manager: ViewportManager,
        menu_bar: MenuBar,
        status_bar: GUIStatusBar,
        fps_timer: FPSTimer,
        audio_settings_window: GUIAudioSettingsWindow,
        reconstruction_coordinator: ReconstructionCoordinator,
        playback_router: PlaybackRouter,
        *,
        main_tab: MainTabCoordinator,
        reconstructions_tab: ReconstructionsTabCoordinator,
        sequencer_tab: SequencerTabCoordinator,
        instructions_tab: InstructionsTabCoordinator,
    ) -> None:
        self._session_manager = session_manager
        self._language_manager = language_manager
        self._shortcut_manager = shortcut_manager
        self._layout = layout
        self._theme = theme
        self._viewport_manager = viewport_manager
        self._menu_bar = menu_bar
        self._status_bar = status_bar
        self._fps_timer = fps_timer
        self._audio_settings_window = audio_settings_window
        self._reconstruction_coordinator = reconstruction_coordinator
        self._playback_router = playback_router
        self._main_tab = main_tab
        self._reconstructions_tab = reconstructions_tab
        self._sequencer_tab = sequencer_tab
        self._instructions_tab = instructions_tab

    def setup(
        self,
        bindings: ShortcutBindings,
        *,
        on_close: Callback,
        on_tab_changed: Callback,
    ) -> None:
        dpg.create_context()
        self._set_fonts()
        self._register_shortcuts(bindings)
        self._set_default_theme()
        self._viewport_manager.create_viewport()
        self._setup_dearpygui()
        self._setup_handlers()
        self._create_main_window(on_tab_changed)
        self._start_callback_worker()
        dpg.set_exit_callback(on_close)

    def _start_callback_worker(self) -> None:
        CallbackQueue.start()

    def _setup_dearpygui(self) -> None:
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.render_dearpygui_frame()

    def _set_fonts(self) -> None:
        FontRegistry.register_fonts(self._layout.general.fonts.scale)

    def _set_default_theme(self) -> None:
        self._theme.bind()

    def _register_shortcuts(self, bindings: ShortcutBindings) -> None:
        self._shortcut_manager.register(
            ShortcutId.NEW_PROJECT,
            Shortcut(dpg.mvKey_N, (Modifier.CTRL,)),
            bindings.new_project,
        )
        self._shortcut_manager.register(
            ShortcutId.OPEN_PROJECT,
            Shortcut(dpg.mvKey_O, (Modifier.CTRL,)),
            bindings.open_project,
        )
        self._shortcut_manager.register(
            ShortcutId.SAVE_PROJECT,
            Shortcut(dpg.mvKey_S, (Modifier.CTRL,)),
            bindings.save_project,
        )
        self._shortcut_manager.register(
            ShortcutId.SAVE_PROJECT_AS,
            Shortcut(dpg.mvKey_S, (Modifier.CTRL, Modifier.SHIFT)),
            bindings.save_project_as,
        )
        self._shortcut_manager.register(
            ShortcutId.CLOSE_PROJECT,
            Shortcut(dpg.mvKey_W, (Modifier.CTRL,)),
            bindings.close_project,
        )
        self._shortcut_manager.register(
            ShortcutId.SAVE_RECONSTRUCTION,
            Shortcut(dpg.mvKey_S, (Modifier.CTRL, Modifier.ALT)),
            bindings.save_reconstruction,
        )
        self._shortcut_manager.register(
            ShortcutId.SAVE_RECONSTRUCTION_AS,
            Shortcut(dpg.mvKey_S, (Modifier.CTRL, Modifier.ALT, Modifier.SHIFT)),
            bindings.save_reconstruction_as,
        )
        self._shortcut_manager.register(
            ShortcutId.LOAD_RECONSTRUCTION,
            Shortcut(dpg.mvKey_O, (Modifier.CTRL, Modifier.ALT)),
            bindings.load_reconstruction,
        )
        self._shortcut_manager.register(
            ShortcutId.CLOSE_RECONSTRUCTION,
            Shortcut(dpg.mvKey_W, (Modifier.CTRL, Modifier.ALT)),
            bindings.close_reconstruction,
        )
        self._shortcut_manager.register(
            ShortcutId.SAVE_GENERATION_SETTINGS,
            Shortcut(),
            bindings.save_config,
        )
        self._shortcut_manager.register(
            ShortcutId.LOAD_GENERATION_SETTINGS,
            Shortcut(),
            bindings.load_config,
        )
        self._shortcut_manager.register(
            ShortcutId.AUDIO_SETTINGS,
            Shortcut(dpg.mvKey_A, (Modifier.CTRL,)),
            bindings.audio_settings,
        )
        self._shortcut_manager.register(
            ShortcutId.EXIT,
            Shortcut(dpg.mvKey_F4, (Modifier.ALT,)),
            bindings.exit,
        )
        self._shortcut_manager.register(
            ShortcutId.RECONSTRUCT_FILE,
            Shortcut(dpg.mvKey_R, (Modifier.CTRL,)),
            bindings.reconstruct_file,
        )
        self._shortcut_manager.register(
            ShortcutId.RECONSTRUCT_DIRECTORY,
            Shortcut(dpg.mvKey_R, (Modifier.CTRL, Modifier.SHIFT)),
            bindings.reconstruct_directory,
        )
        self._shortcut_manager.register(
            ShortcutId.EXPORT_RECONSTRUCTION_WAV,
            Shortcut(dpg.mvKey_E, (Modifier.CTRL,)),
            bindings.export_wav,
        )
        self._shortcut_manager.register(
            ShortcutId.EXPORT_RECONSTRUCTION_FTIS,
            Shortcut(dpg.mvKey_I, (Modifier.CTRL,)),
            bindings.export_ftis,
        )
        self._shortcut_manager.register(
            ShortcutId.TOGGLE_FULLSCREEN,
            Shortcut(dpg.mvKey_F11),
            bindings.toggle_fullscreen,
        )
        self._shortcut_manager.register(
            ShortcutId.TOGGLE_ADVANCED_SETTINGS,
            Shortcut(dpg.mvKey_A, (Modifier.CTRL, Modifier.SHIFT)),
            bindings.toggle_advanced_settings,
        )
        self._shortcut_manager.register(
            ShortcutId.PLAY,
            Shortcut(dpg.mvKey_Spacebar),
            bindings.play,
        )
        self._shortcut_manager.register(
            ShortcutId.PLAY_FROM_START,
            Shortcut(dpg.mvKey_Spacebar, (Modifier.SHIFT,)),
            bindings.play_from_start,
        )
        self._shortcut_manager.register(
            ShortcutId.STOP,
            Shortcut(dpg.mvKey_Spacebar, (Modifier.CTRL,)),
            bindings.stop,
        )
        self._shortcut_manager.register(
            ShortcutId.TOGGLE_AUTOPLAY,
            Shortcut(dpg.mvKey_P, (Modifier.CTRL,)),
            bindings.toggle_autoplay,
        )

        self._shortcut_manager.bind_all()

    def _setup_handlers(self) -> None:
        self._shortcut_manager.setup_focus_handler()

    def _create_main_window(self, on_tab_changed: Callback) -> None:
        with dpg.window(
            label=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.MAIN_WINDOW,
            ],
            tag=TAG_GLOBAL_WINDOW_MAIN,
        ):
            self._create_menu_bar()
            self._create_tabs(on_tab_changed)
            self._create_status_bar()

        dpg.set_primary_window(TAG_GLOBAL_WINDOW_MAIN, True)

    def _create_menu_bar(self) -> None:
        self._menu_bar.create(self._build_menu_bar_viewmodel())

    def _build_menu_bar_viewmodel(self) -> MenuBarViewModel:
        return MenuBarViewModel(
            reconstruction_loaded=self._reconstruction_coordinator.is_loaded(),
            play_label=self._playback_router.play_label,
            play_or_pause_enabled=self._playback_router.is_play_enabled,
            stop_enabled=self._playback_router.is_stop_enabled,
            autoplay=self._session_manager.autoplay,
            fullscreen=self._session_manager.fullscreen,
            advanced_settings=self._session_manager.advanced_settings,
        )

    def update_menu(self) -> None:
        self._main_tab.sync_advanced_settings_visibility()
        self._menu_bar.update(self._build_menu_bar_viewmodel())

    def _create_tabs(self, on_tab_changed: Callback) -> None:
        with dpg.child_window(
            height=-self._layout.general.status_bar.height,
            border=False,
        ):
            with dpg.tab_bar(
                tag=TAG_GLOBAL_TABS,
                callback=on_tab_changed,
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
            self._status_bar.create()

    def restore_current_items(self, reconstruction_manager: ReconstructionManager) -> None:
        current_tab = self._session_manager.load_current_tab()
        self.set_current_tab(current_tab)
        self.load_current_reconstruction(reconstruction_manager)

    def load_current_reconstruction(self, reconstruction_manager: ReconstructionManager) -> None:
        current_reconstruction = self._session_manager.current_reconstruction
        if current_reconstruction is not None:
            if current_reconstruction.exists():
                try:
                    reconstruction_manager.load_reconstruction(current_reconstruction)
                except LoadReconstructionError:
                    self._session_manager.set_current_reconstruction(None)
            else:
                self._session_manager.set_current_reconstruction(None)

    def open_audio_settings(self) -> None:
        self._audio_settings_window.show()

    def set_current_tab(self, tab: Tab) -> None:
        try:
            resolved = _TAB_TAGS[tab]
        except KeyError as exception:
            raise SystemError(f"Tab {tab} does not have a corresponding DearPyGui tag.") from exception

        dpg.set_value(TAG_GLOBAL_TABS, resolved)
        self._session_manager.set_current_tab(tab)

    def get_current_tab(self) -> Tab:
        current_tab = dpg.get_value(TAG_GLOBAL_TABS)
        alias: str = dpg.get_item_alias(current_tab)
        if alias is None:
            return Tab.MAIN

        try:
            return _TAG_TABS[alias]
        except KeyError as exception:
            raise SystemError(f"Current tab alias {alias} does not correspond to any known Tab.") from exception

    def get_current_player(self) -> Optional[AudioPlayerPanelProtocol]:
        match _TAG_TABS.get(self.get_current_tab()):
            case Tab.RECONSTRUCTIONS:
                return self._reconstructions_tab.player_panel
            case Tab.INSTRUCTIONS:
                return self._instructions_tab.player_panel
            case Tab.SEQUENCER:
                return self._sequencer_tab.player_panel
            case _:
                return None

    def update_fps(self, delta_time: float) -> None:
        fps = self._fps_timer.update(delta_time)
        self._menu_bar.update_fps(fps)

    def update_status_bar(self, delta_time: float) -> None:
        self._status_bar.update(delta_time=delta_time)

    def toggle_fullscreen(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self._viewport_manager.toggle_fullscreen()

    def toggle_autoplay(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self._session_manager.toggle_autoplay()
        self.update_menu()

    def toggle_advanced_settings(
        self,
        sender: Optional[Sender] = None,
        app_data: Optional[Any] = None,
        user_data: Optional[Any] = None,
    ) -> None:
        self._main_tab.toggle_advanced_settings()
        self.update_menu()
