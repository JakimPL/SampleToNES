from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.playback import FollowMode
from sampletones_application.coordinators.playback.protocol import AudioPlayerProtocol
from sampletones_application.coordinators.tabs.instructions import (
    InstructionsTabCoordinator,
)
from sampletones_application.coordinators.tabs.main import MainTabCoordinator
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.coordinators.tabs.sequencer import SequencerTabCoordinator
from sampletones_application.layout import LayoutConfig
from sampletones_application.tags.general import (
    TAG_GLOBAL_STATUS_WINDOW,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
    TAG_GLOBAL_TAB_MAIN,
    TAG_GLOBAL_TAB_RECONSTRUCTION,
    TAG_GLOBAL_TAB_SEQUENCER,
    TAG_GLOBAL_TABS,
    TAG_GLOBAL_THEME_TAB_STRIP,
    TAG_GLOBAL_WINDOW_MAIN,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.menu import MenuBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.fps import FPSTimer
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.ids import (
    CHANNEL_SHORTCUT_IDS,
    FOLLOW_MODE_SHORTCUT_IDS,
    PROJECT_EXPORT_SHORTCUT_IDS,
    SAMPLE_EXPORT_SHORTCUT_IDS,
    ShortcutId,
)
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_application.viewport import ViewportManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.trackers.format import TrackerFormat
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback, PathCallback

_TAB_TAGS: Dict[Tab, str] = {
    Tab.MAIN: TAG_GLOBAL_TAB_MAIN,
    Tab.RECONSTRUCTIONS: TAG_GLOBAL_TAB_RECONSTRUCTION,
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
    export_project: Callable[[TrackerFormat], None]
    render_song: Callback
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
    export_instruments: Callable[[TrackerFormat], None]
    add_reconstruction_to_sequencer: Callback
    open_reconstruction_in_explorer: Callback
    locate_original_audio: Callback
    play: Callback
    play_from_start: Callback
    play_from_frame: Callback
    stop: Callback
    toggle_autoplay: Callback
    set_follow_mode: Callable[[FollowMode], None]
    toggle_loop_song: Callback
    toggle_channel: Callable[[GeneratorName], None]
    unmute_all_channels: Callback
    audio_settings: Callback
    display_settings: Callback
    keyboard_settings: Callback
    toggle_advanced_settings: Callback
    toggle_fullscreen: Callback
    about: Callback
    next_tab: Callback
    previous_tab: Callback


class ApplicationShell:
    """
    The translation layer between the Python application and the DPG framework.

    It serves two roles:

    - *Lifecycle* — encodes the DPG initialisation sequence in ``setup()`` and
      hides it behind a clean boundary.
    - *Runtime* — tab router, shortcut dispatcher, and per-frame UI driver.

    The shell stays free of domain state: it translates between the UI and the coordinators,
    which make the decisions.
    """

    def __init__(
        self,
        *,
        session_manager: SessionManager,
        language_manager: LanguageManager,
        shortcut_manager: ShortcutManager,
        key_router: KeyRouter,
        layout: LayoutConfig,
        theme: Theme,
        viewport_manager: ViewportManager,
        menu_bar: MenuBar,
        status_bar: GUIStatusBar,
        fps_timer: FPSTimer,
        main_tab: MainTabCoordinator,
        reconstructions_tab: ReconstructionTabCoordinator,
        sequencer_tab: SequencerTabCoordinator,
        instructions_tab: InstructionsTabCoordinator,
    ) -> None:
        self._session_manager = session_manager
        self._language_manager = language_manager
        self._shortcut_manager = shortcut_manager
        self._key_router = key_router
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
        self._activate_background_work()
        dpg.set_exit_callback(on_close)

    def _activate_background_work(self) -> None:
        """Re-arm the background machinery for this run.

        Clears any shutdown request left by a previous teardown so the executor
        runs tasks again, and marks the callback queue live so pending results
        drain. Symmetric with :func:`stop_background_workers`, which sets the
        shutdown flag and stops the queue.
        """
        SingleThreadExecutor.reset_shutdown()
        CallbackQueue.start()

    def _setup_dearpygui(self) -> None:
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.render_dearpygui_frame()
        self._viewport_manager.apply_fullscreen_state()

    def _set_fonts(self) -> None:
        FontRegistry.register_fonts(self._layout.fonts.scale)

    def _set_default_theme(self) -> None:
        self._theme.bind()

    def _register_shortcuts(self, bindings: ShortcutBindings) -> None:
        """Names the call each application action makes, then binds the scope to the key router.

        Which combination reaches an action is the keybinding scheme's to say, so the shell states
        only the pairing of an action with its coordinator call.
        """
        for shortcut_id, callback in ApplicationShell._shortcut_callbacks(bindings).items():
            self._shortcut_manager.register(shortcut_id, callback)

        self._shortcut_manager.bind_all()

    @staticmethod
    def _shortcut_callbacks(bindings: ShortcutBindings) -> Dict[ShortcutId, Callback]:
        """The call every application action makes, one entry per action the menus offer."""
        return {
            ShortcutId.NEW_PROJECT: bindings.new_project,
            ShortcutId.OPEN_PROJECT: bindings.open_project,
            ShortcutId.SAVE_PROJECT: bindings.save_project,
            ShortcutId.SAVE_PROJECT_AS: bindings.save_project_as,
            ShortcutId.PROJECT_PROPERTIES: bindings.project_properties,
            ShortcutId.RENDER_SONG: bindings.render_song,
            ShortcutId.CLOSE_PROJECT: bindings.close_project,
            ShortcutId.EXIT: bindings.exit,
            ShortcutId.UNDO: bindings.undo,
            ShortcutId.REDO: bindings.redo,
            ShortcutId.RECONSTRUCT_FILE: bindings.reconstruct_file,
            ShortcutId.RECONSTRUCT_DIRECTORY: bindings.reconstruct_directory,
            ShortcutId.LOAD_GENERATION_SETTINGS: bindings.load_generation_settings,
            ShortcutId.SAVE_GENERATION_SETTINGS: bindings.save_generation_settings,
            ShortcutId.OPEN_RECONSTRUCTION: bindings.open_reconstruction,
            ShortcutId.SAVE_RECONSTRUCTION: bindings.save_reconstruction,
            ShortcutId.SAVE_RECONSTRUCTION_AS: bindings.save_reconstruction_as,
            ShortcutId.CLOSE_RECONSTRUCTION: bindings.close_reconstruction,
            ShortcutId.EXPORT_RECONSTRUCTION_WAV: bindings.export_wav,
            ShortcutId.ADD_RECONSTRUCTION_TO_SEQUENCER: bindings.add_reconstruction_to_sequencer,
            ShortcutId.OPEN_RECONSTRUCTION_IN_EXPLORER: bindings.open_reconstruction_in_explorer,
            ShortcutId.LOCATE_ORIGINAL_AUDIO: bindings.locate_original_audio,
            ShortcutId.PLAY: bindings.play,
            ShortcutId.PLAY_FROM_START: bindings.play_from_start,
            ShortcutId.PLAY_FROM_FRAME: bindings.play_from_frame,
            ShortcutId.STOP: bindings.stop,
            ShortcutId.TOGGLE_AUTOPLAY: bindings.toggle_autoplay,
            ShortcutId.TOGGLE_LOOP_SONG: bindings.toggle_loop_song,
            ShortcutId.AUDIO_SETTINGS: bindings.audio_settings,
            ShortcutId.DISPLAY_SETTINGS: bindings.display_settings,
            ShortcutId.KEYBOARD_SETTINGS: bindings.keyboard_settings,
            ShortcutId.TOGGLE_ADVANCED_SETTINGS: bindings.toggle_advanced_settings,
            ShortcutId.TOGGLE_FULLSCREEN: bindings.toggle_fullscreen,
            ShortcutId.ABOUT_DIALOG: bindings.about,
            ShortcutId.NEXT_TAB: bindings.next_tab,
            ShortcutId.PREVIOUS_TAB: bindings.previous_tab,
            **ApplicationShell._export_callbacks(bindings),
            **ApplicationShell._follow_mode_callbacks(bindings),
            **ApplicationShell._channel_callbacks(bindings),
        }

    @staticmethod
    def _export_callbacks(
        bindings: ShortcutBindings,
    ) -> Dict[ShortcutId, Callback]:
        """One export action per tracker format, the entries the Export submenus list.

        Each action carries the format it writes, so a menu entry and its key combination reach
        the same coordinator call.
        """
        project = {
            shortcut_id: partial(bindings.export_project, tracker_format)
            for tracker_format, shortcut_id in PROJECT_EXPORT_SHORTCUT_IDS.items()
        }
        instruments = {
            shortcut_id: partial(bindings.export_instruments, tracker_format)
            for tracker_format, shortcut_id in SAMPLE_EXPORT_SHORTCUT_IDS.items()
        }
        return {**project, **instruments}

    @staticmethod
    def _follow_mode_callbacks(
        bindings: ShortcutBindings,
    ) -> Dict[ShortcutId, Callback]:
        """One action per reach the sequencer view follows the playhead at.

        Each action carries the mode it chooses, so a key press and the Follow playback submenu
        item beside it settle on the same reach.
        """
        return {
            shortcut_id: partial(bindings.set_follow_mode, mode)
            for mode, shortcut_id in FOLLOW_MODE_SHORTCUT_IDS.items()
        }

    @staticmethod
    def _channel_callbacks(bindings: ShortcutBindings) -> Dict[ShortcutId, Callback]:
        """One action per tracker channel, plus the one that brings the whole mix back.

        Each action carries the channel it switches, so the Playback menu lists them as its
        Channels submenu.
        """
        channels: Dict[ShortcutId, Callback] = {
            shortcut_id: partial(bindings.toggle_channel, generator)
            for generator, shortcut_id in CHANNEL_SHORTCUT_IDS.items()
        }
        return {
            **channels,
            ShortcutId.UNMUTE_ALL_CHANNELS: bindings.unmute_all_channels,
        }

    def _setup_handlers(self) -> None:
        self._key_router.bind()

    def _create_main_window(
        self,
        on_tab_changed: Callback,
        initial_menu_state: MenuBarViewModel,
    ) -> None:
        with dpg.window(
            label=self._language_manager["global.dialog.title.main_window"],
            tag=TAG_GLOBAL_WINDOW_MAIN,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        ):
            self._menu_bar.create(initial_menu_state)
            self._create_tabs(on_tab_changed)
            self._create_status_bar()

        dpg.set_primary_window(TAG_GLOBAL_WINDOW_MAIN, True)
        dpg.set_viewport_resize_callback(self._sync_responsive_layout)

    def _sync_responsive_layout(
        self,
        _sender: Optional[Sender] = None,
        _app_data: Optional[Any] = None,
        _user_data: Optional[Any] = None,
    ) -> None:
        """Refits every tab's responsive columns and graphs to the resized viewport."""
        self._main_tab.sync_responsive_layout()
        self._reconstructions_tab.sync_responsive_layout()
        self._sequencer_tab.sync_responsive_layout()
        self._instructions_tab.sync_responsive_layout()

    def update_menu(self, state: MenuBarViewModel) -> None:
        self._main_tab.sync_advanced_settings_visibility()
        self._menu_bar.update(state)

    def _create_tabs(self, on_tab_changed: Callback) -> None:
        status_bar_layout = self._layout.general.status_bar
        with (
            dpg.child_window(
                height=-(status_bar_layout.height + status_bar_layout.reserved_margin),
                border=False,
                no_scrollbar=True,
                no_scroll_with_mouse=True,
            ) as tab_container,
            dpg.tab_bar(
                tag=TAG_GLOBAL_TABS,
                callback=on_tab_changed,
            ),
        ):
            self._main_tab.create_tab()
            self._reconstructions_tab.create_tab()
            self._sequencer_tab.create_tab()
            self._instructions_tab.create_tab()

        ThemeRegistry.get(TAG_GLOBAL_THEME_TAB_STRIP).bind_to_item(tab_container)
        for tab_tag in (
            TAG_GLOBAL_TAB_MAIN,
            TAG_GLOBAL_TAB_RECONSTRUCTION,
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

    def _restore_current_reconstruction(
        self,
        on_load_reconstruction: PathCallback,
    ) -> None:
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

    def get_active_source(self) -> Optional[AudioPlayerProtocol]:
        """The active tab's own playback source, or ``None`` when it owns only previews (Main)."""
        match self.get_current_tab():
            case Tab.MAIN:
                return None
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
