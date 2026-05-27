import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
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
    LBL_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
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
    TPL_MENU_TEXT_FPS,
)
from sampletones_application.logic.menu.viewmodel import MenuBarViewModel
from sampletones_application.ui.themes.fps import FPSTimerTheme
from sampletones_application.utils.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.utils.shortcuts.shortcut import ShortcutId


class MenuBar:
    def __init__(
        self,
        *,
        shortcut_manager: ShortcutManager,
        fps_theme: FPSTimerTheme,
    ) -> None:
        self._shortcut_manager = shortcut_manager
        self._fps_theme = fps_theme

    def create(self, state: MenuBarViewModel) -> None:
        with dpg.menu_bar():
            with dpg.menu(label=LBL_MENU_GROUP_GENERAL):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.AUDIO_SETTINGS,
                    label=LBL_MENU_ITEM_GENERAL_AUDIO_SETTINGS,
                )
                dpg.add_separator()
                self._shortcut_manager.add_menu_item(
                    ShortcutId.EXIT,
                    label=LBL_MENU_ITEM_GENERAL_EXIT,
                )
            with dpg.menu(label=LBL_MENU_GROUP_RECONSTRUCTION):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_SAVE,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_SAVE,
                    enabled=state.reconstruction_loaded,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_RECONSTRUCTION_AS,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
                    enabled=state.reconstruction_loaded,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.CLOSE_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_CLOSE,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_CLOSE,
                    enabled=state.reconstruction_loaded,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.LOAD_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_LOAD,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_LOAD,
                    enabled=not state.reconstruction_loaded,
                )
                dpg.add_separator()
                self._shortcut_manager.add_menu_item(
                    ShortcutId.RECONSTRUCT_FILE,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.RECONSTRUCT_DIRECTORY,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
                )
                dpg.add_separator()
                self._shortcut_manager.add_menu_item(
                    ShortcutId.EXPORT_RECONSTRUCTION_WAV,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV,
                    enabled=state.reconstruction_loaded,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.EXPORT_RECONSTRUCTION_FTIS,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS,
                    label=LBL_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS,
                    enabled=state.reconstruction_loaded,
                )
            with dpg.menu(label=LBL_MENU_GROUP_CONFIGURATION):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_CONFIGURATION,
                    label=LBL_MENU_ITEM_CONFIGURATION_SAVE_CONFIG,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.LOAD_CONFIGURATION,
                    label=LBL_MENU_ITEM_CONFIGURATION_LOAD_CONFIG,
                )
            with dpg.menu(label=LBL_MENU_GROUP_PLAYBACK):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.PLAY,
                    tag=TAG_MENU_ITEM_PLAYBACK_PLAY,
                    label=state.play_label,
                    enabled=state.play_or_pause_enabled,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.PLAY_FROM_START,
                    tag=TAG_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
                    label=LBL_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
                    enabled=state.play_or_pause_enabled,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.STOP,
                    tag=TAG_MENU_ITEM_PLAYBACK_STOP,
                    label=LBL_MENU_ITEM_PLAYBACK_STOP,
                    enabled=state.stop_enabled,
                )
                dpg.add_separator()
                self._shortcut_manager.add_menu_item(
                    ShortcutId.TOGGLE_AUTOPLAY,
                    tag=TAG_MENU_ITEM_PLAYBACK_AUTOPLAY,
                    label=LBL_MENU_ITEM_PLAYBACK_AUTOPLAY,
                    check=True,
                )
            with dpg.menu(label=LBL_MENU_GROUP_VIEW):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.TOGGLE_ADVANCED_SETTINGS,
                    tag=TAG_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
                    label=LBL_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
                    check=True,
                )
                self._shortcut_manager.add_menu_item(
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
            self._fps_theme.bind_to_item(TAG_MENU_TEXT_FPS)

    def update(self, state: MenuBarViewModel) -> None:
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV, enabled=state.reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS, enabled=state.reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_CLOSE, enabled=state.reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_SAVE, enabled=state.reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_RECONSTRUCTION_SAVE_AS, enabled=state.reconstruction_loaded)
        dpg_configure_item(TAG_MENU_ITEM_PLAYBACK_PLAY_FROM_START, enabled=state.play_or_pause_enabled)
        dpg_configure_item(
            TAG_MENU_ITEM_PLAYBACK_PLAY,
            label=state.play_label,
            enabled=state.play_or_pause_enabled,
        )
        dpg_configure_item(TAG_MENU_ITEM_PLAYBACK_STOP, enabled=state.stop_enabled)
        dpg_set_value(TAG_MENU_ITEM_PLAYBACK_AUTOPLAY, state.autoplay)
        dpg_set_value(TAG_MENU_ITEM_VIEW_FULLSCREEN, state.fullscreen)
        dpg_set_value(TAG_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS, state.advanced_settings)

    def update_fps(self, fps: float) -> None:
        dpg_configure_item(TAG_MENU_TEXT_FPS, label=TPL_MENU_TEXT_FPS.format(fps=fps))
