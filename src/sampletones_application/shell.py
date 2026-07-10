from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    GlobalDialogTitleElements,
)
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
    TAG_GLOBAL_THEME_PANEL_GROUND,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.coordinators.instructions import InstructionsTabCoordinator
from sampletones_application.coordinators.main import MainTabCoordinator
from sampletones_application.coordinators.playback import AudioPlayerProtocol
from sampletones_application.coordinators.reconstructions import (
    ReconstructionsTabCoordinator,
)
from sampletones_application.coordinators.sequencer import SequencerTabCoordinator
from sampletones_application.layout import LayoutConfig
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.menu import MenuBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.fps import FPSTimer
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.keys import Modifier
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_application.viewport import ViewportManager
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback, PathCallback

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
    project_properties: Callback
    export_project_module: Callback
    close_project: Callback
    exit: Callback
    undo: Callback
    redo: Callback
    reconstruct_file: Callback
    reconstruct_directory: Callback
    load_generation_settings: Callback
    save_generation_settings: Callback
    open_reconstruction: Callback
    save_reconstruction: Callback
    save_reconstruction_as: Callback
    close_reconstruction: Callback
    export_wav: Callback
    export_instruments: Callback
    add_reconstruction_to_sequencer: Callback
    open_reconstruction_in_explorer: Callback
    locate_original_audio: Callback
    play: Callback
    play_from_start: Callback
    stop: Callback
    toggle_autoplay: Callback
    toggle_follow_playback: Callback
    toggle_loop_song: Callback
    audio_settings: Callback
    toggle_advanced_settings: Callback
    toggle_fullscreen: Callback
    about: Callback


class ApplicationShell:
    """
    The translation layer between the Python application and the DPG framework.

    It serves two roles:

    - *Lifecycle* — encodes the DPG initialisation sequence in ``setup()`` and
      hides it behind a clean boundary.
    - *Runtime* — tab router, shortcut dispatcher, and per-frame UI driver.

    The shell must remain free of domain state — it translates, not decides.
    """

    def __init__(
        self,
        *,
        session_manager: SessionManager,
        language_manager: LanguageManager,
        shortcut_manager: ShortcutManager,
        layout: LayoutConfig,
        theme: Theme,
        viewport_manager: ViewportManager,
        menu_bar: MenuBar,
        status_bar: GUIStatusBar,
        fps_timer: FPSTimer,
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
        initial_menu_state: MenuBarViewModel,
    ) -> None:
        dpg.create_context()
        self._set_fonts()
        self._register_shortcuts(bindings)
        self._set_default_theme()
        self._viewport_manager.create_viewport()
        self._setup_dearpygui()
        self._setup_handlers()
        self._create_main_window(on_tab_changed, initial_menu_state)
        self._start_callback_worker()
        dpg.set_exit_callback(on_close)

    def _start_callback_worker(self) -> None:
        CallbackQueue.start()

    def _setup_dearpygui(self) -> None:
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.render_dearpygui_frame()
        self._viewport_manager.apply_fullscreen_state()

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
            ShortcutId.EXPORT_PROJECT_MODULE,
            Shortcut(dpg.mvKey_M, (Modifier.CTRL,)),
            bindings.export_project_module,
        )
        self._shortcut_manager.register(
            ShortcutId.PROJECT_PROPERTIES,
            Shortcut(dpg.mvKey_P, (Modifier.ALT,)),
            bindings.project_properties,
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
            ShortcutId.OPEN_RECONSTRUCTION,
            Shortcut(dpg.mvKey_O, (Modifier.CTRL, Modifier.ALT)),
            bindings.open_reconstruction,
        )
        self._shortcut_manager.register(
            ShortcutId.CLOSE_RECONSTRUCTION,
            Shortcut(dpg.mvKey_W, (Modifier.CTRL, Modifier.ALT)),
            bindings.close_reconstruction,
        )
        self._shortcut_manager.register(
            ShortcutId.SAVE_GENERATION_SETTINGS,
            Shortcut(),
            bindings.save_generation_settings,
        )
        self._shortcut_manager.register(
            ShortcutId.LOAD_GENERATION_SETTINGS,
            Shortcut(),
            bindings.load_generation_settings,
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
            ShortcutId.EXPORT_RECONSTRUCTION_INSTRUMENTS,
            Shortcut(dpg.mvKey_I, (Modifier.CTRL,)),
            bindings.export_instruments,
        )
        self._shortcut_manager.register(
            ShortcutId.ADD_RECONSTRUCTION_TO_SEQUENCER,
            Shortcut(),
            bindings.add_reconstruction_to_sequencer,
        )
        self._shortcut_manager.register(
            ShortcutId.OPEN_RECONSTRUCTION_IN_EXPLORER,
            Shortcut(),
            bindings.open_reconstruction_in_explorer,
        )
        self._shortcut_manager.register(
            ShortcutId.LOCATE_ORIGINAL_AUDIO,
            Shortcut(),
            bindings.locate_original_audio,
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
        self._shortcut_manager.register(
            ShortcutId.TOGGLE_FOLLOW_PLAYBACK,
            Shortcut(),
            bindings.toggle_follow_playback,
        )
        self._shortcut_manager.register(
            ShortcutId.TOGGLE_LOOP_SONG,
            Shortcut(),
            bindings.toggle_loop_song,
        )
        self._shortcut_manager.register(
            ShortcutId.UNDO,
            Shortcut(dpg.mvKey_Z, (Modifier.CTRL,)),
            bindings.undo,
        )
        self._shortcut_manager.register(
            ShortcutId.REDO,
            Shortcut(dpg.mvKey_Y, (Modifier.CTRL,)),
            bindings.redo,
        )
        self._shortcut_manager.register_alias(
            ShortcutId.REDO,
            Shortcut(dpg.mvKey_Z, (Modifier.CTRL, Modifier.SHIFT)),
        )
        self._shortcut_manager.register(
            ShortcutId.ABOUT_DIALOG,
            Shortcut(),
            bindings.about,
        )

        self._shortcut_manager.bind_all()

    def _setup_handlers(self) -> None:
        self._shortcut_manager.setup_focus_handler()

    def _create_main_window(self, on_tab_changed: Callback, initial_menu_state: MenuBarViewModel) -> None:
        with dpg.window(
            label=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.MAIN_WINDOW,
            ],
            tag=TAG_GLOBAL_WINDOW_MAIN,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        ):
            self._menu_bar.create(initial_menu_state)
            self._create_tabs(on_tab_changed)
            self._create_status_bar()

        dpg.set_primary_window(TAG_GLOBAL_WINDOW_MAIN, True)

    def update_menu(self, state: MenuBarViewModel) -> None:
        self._main_tab.sync_advanced_settings_visibility()
        self._menu_bar.update(state)

    def _create_tabs(self, on_tab_changed: Callback) -> None:
        status_bar_layout = self._layout.general.status_bar
        with dpg.child_window(
            height=-(status_bar_layout.height + status_bar_layout.reserved_margin),
            border=False,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        ) as tab_container:
            with dpg.tab_bar(
                tag=TAG_GLOBAL_TABS,
                callback=on_tab_changed,
            ):
                self._main_tab.create_tab()
                self._reconstructions_tab.create_tab()
                self._sequencer_tab.create_tab()
                self._instructions_tab.create_tab()

        ThemeRegistry.get(TAG_GLOBAL_THEME_PANEL_GROUND).bind_to_item(tab_container)
        for tab_tag in (
            TAG_GLOBAL_TAB_MAIN,
            TAG_GLOBAL_TAB_RECONSTRUCTIONS,
            TAG_GLOBAL_TAB_SEQUENCER,
            TAG_GLOBAL_TAB_INSTRUCTIONS,
        ):
            FontRegistry.bind_to_item(tab_tag, Font.REGULAR_LARGE)
            label = dpg.get_item_configuration(tab_tag)["label"]
            dpg.configure_item(tab_tag, label=f"  {label}  ")
            for content in dpg.get_item_children(tab_tag, 1) or []:
                FontRegistry.bind_to_item(content, Font.REGULAR)

    def _create_status_bar(self) -> None:
        with dpg.child_window(
            tag=TAG_GLOBAL_STATUS_WINDOW,
            parent=TAG_GLOBAL_WINDOW_MAIN,
            width=-1,
            height=self._layout.general.status_bar.height,
            indent=0,
            border=False,
            menubar=True,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        ):
            self._status_bar.create()

    def restore_current_items(
        self,
        library_path: Optional[Path] = None,
        reconstruction_path: Optional[Path] = None,
        project_path: Optional[Path] = None,
        *,
        on_load_library: PathCallback,
        on_load_project: PathCallback,
        on_load_reconstruction: PathCallback,
    ) -> None:
        current_tab = self._session_manager.load_current_tab()
        self.set_current_tab(current_tab)

        if library_path is not None:
            on_load_library(library_path)

        if reconstruction_path is not None:
            on_load_reconstruction(reconstruction_path)
        else:
            self._restore_current_reconstruction(on_load_reconstruction)

        if project_path is not None:
            on_load_project(project_path)
        else:
            self._restore_current_project(on_load_project)

    def _restore_current_project(self, on_load_project: PathCallback) -> None:
        current_project_path = self._session_manager.current_project
        if current_project_path is None:
            return

        on_load_project(current_project_path)

    def _restore_current_reconstruction(self, on_load_reconstruction: PathCallback) -> None:
        current_reconstruction_path = self._session_manager.current_reconstruction
        if current_reconstruction_path is None:
            return

        on_load_reconstruction(current_reconstruction_path)

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

    def get_current_player(self) -> AudioPlayerProtocol:
        match self.get_current_tab():
            case Tab.MAIN:
                return self._main_tab.player
            case Tab.RECONSTRUCTIONS:
                return self._reconstructions_tab.player
            case Tab.INSTRUCTIONS:
                return self._instructions_tab.player
            case Tab.SEQUENCER:
                return self._sequencer_tab.player

    def update_fps(self, delta_time: float) -> None:
        fps = self._fps_timer.update(delta_time)
        self._menu_bar.update_fps(fps)

    def update_status_bar(self, delta_time: float) -> None:
        self._status_bar.update(delta_time=delta_time)

    def toggle_fullscreen(
        self,
        _sender: Optional[Sender] = None,
        _app_data: Optional[Any] = None,
        _user_data: Optional[Any] = None,
    ) -> None:
        self._viewport_manager.toggle_fullscreen()
