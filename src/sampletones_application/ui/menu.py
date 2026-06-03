import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
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
    TAG_TEXT_GLOBAL_MENU_FPS,
)
from sampletones_application.text.elements.global_ import GlobalTemplateElements, MenuElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.ui.themes.fps import FPSTimerTheme
from sampletones_application.utils.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.utils.shortcuts.shortcut import ShortcutId
from sampletones_application.view_model.shared.menu import MenuBarViewModel


class MenuBar:
    def __init__(
        self,
        *,
        shortcut_manager: ShortcutManager,
        fps_theme: FPSTimerTheme,
        language_manager: LanguageManager,
    ) -> None:
        self._shortcut_manager = shortcut_manager
        self._fps_theme = fps_theme

        self._lbl_group_general = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.GROUP_GENERAL)
        ]
        self._lbl_group_configuration = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.GROUP_CONFIGURATION)
        ]
        self._lbl_group_reconstruction = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.GROUP_RECONSTRUCTION)
        ]
        self._lbl_group_playback = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.GROUP_PLAYBACK)
        ]
        self._lbl_group_view = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.GROUP_VIEW)
        ]
        self._lbl_item_audio_settings = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_AUDIO_SETTINGS)
        ]
        self._lbl_item_exit = language_manager[TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_EXIT)]
        self._lbl_item_config_save = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_CONFIG_SAVE)
        ]
        self._lbl_item_config_load = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_CONFIG_LOAD)
        ]
        self._lbl_item_reconstruct_file = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_RECONSTRUCTION_RECONSTRUCT_FILE)
        ]
        self._lbl_item_reconstruct_directory = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY)
        ]
        self._lbl_item_reconstruction_save = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_RECONSTRUCTION_SAVE)
        ]
        self._lbl_item_reconstruction_save_as = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_RECONSTRUCTION_SAVE_AS)
        ]
        self._lbl_item_reconstruction_load = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_RECONSTRUCTION_LOAD)
        ]
        self._lbl_item_reconstruction_close = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_RECONSTRUCTION_CLOSE)
        ]
        self._lbl_item_export_wav = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_RECONSTRUCTION_EXPORT_WAV)
        ]
        self._lbl_item_export_ftis = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_RECONSTRUCTION_EXPORT_FTIS)
        ]
        self._lbl_item_play_from_start = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_PLAYBACK_PLAY_FROM_START)
        ]
        self._lbl_item_stop = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_PLAYBACK_STOP)
        ]
        self._lbl_item_autoplay = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_PLAYBACK_AUTOPLAY)
        ]
        self._lbl_item_fullscreen = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_VIEW_FULLSCREEN)
        ]
        self._lbl_item_show_advanced_settings = language_manager[
            TextKey(Page.GLOBAL, Panel.MENU, TextType.LABEL, MenuElements.ITEM_VIEW_SHOW_ADVANCED_SETTINGS)
        ]
        self._tpl_fps = language_manager[
            TextKey(Page.GLOBAL, Panel.DIALOG, TextType.TEMPLATE, GlobalTemplateElements.FPS)
        ]

    def create(self, state: MenuBarViewModel) -> None:
        with dpg.menu_bar():
            with dpg.menu(label=self._lbl_group_general):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.AUDIO_SETTINGS,
                    label=self._lbl_item_audio_settings,
                )
                dpg.add_separator()
                self._shortcut_manager.add_menu_item(
                    ShortcutId.EXIT,
                    label=self._lbl_item_exit,
                )
            with dpg.menu(label=self._lbl_group_reconstruction):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_SAVE,
                    label=self._lbl_item_reconstruction_save,
                    enabled=state.reconstruction_loaded,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_RECONSTRUCTION_AS,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
                    label=self._lbl_item_reconstruction_save_as,
                    enabled=state.reconstruction_loaded,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.CLOSE_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_CLOSE,
                    label=self._lbl_item_reconstruction_close,
                    enabled=state.reconstruction_loaded,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.LOAD_RECONSTRUCTION,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_LOAD,
                    label=self._lbl_item_reconstruction_load,
                    enabled=not state.reconstruction_loaded,
                )
                dpg.add_separator()
                self._shortcut_manager.add_menu_item(
                    ShortcutId.RECONSTRUCT_FILE,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
                    label=self._lbl_item_reconstruct_file,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.RECONSTRUCT_DIRECTORY,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
                    label=self._lbl_item_reconstruct_directory,
                )
                dpg.add_separator()
                self._shortcut_manager.add_menu_item(
                    ShortcutId.EXPORT_RECONSTRUCTION_WAV,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_WAV,
                    label=self._lbl_item_export_wav,
                    enabled=state.reconstruction_loaded,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.EXPORT_RECONSTRUCTION_FTIS,
                    tag=TAG_MENU_ITEM_RECONSTRUCTION_EXPORT_TO_FTIS,
                    label=self._lbl_item_export_ftis,
                    enabled=state.reconstruction_loaded,
                )
            with dpg.menu(label=self._lbl_group_configuration):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.SAVE_CONFIGURATION,
                    label=self._lbl_item_config_save,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.LOAD_CONFIGURATION,
                    label=self._lbl_item_config_load,
                )
            with dpg.menu(label=self._lbl_group_playback):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.PLAY,
                    tag=TAG_MENU_ITEM_PLAYBACK_PLAY,
                    label=state.play_label,
                    enabled=state.play_or_pause_enabled,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.PLAY_FROM_START,
                    tag=TAG_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
                    label=self._lbl_item_play_from_start,
                    enabled=state.play_or_pause_enabled,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.STOP,
                    tag=TAG_MENU_ITEM_PLAYBACK_STOP,
                    label=self._lbl_item_stop,
                    enabled=state.stop_enabled,
                )
                dpg.add_separator()
                self._shortcut_manager.add_menu_item(
                    ShortcutId.TOGGLE_AUTOPLAY,
                    tag=TAG_MENU_ITEM_PLAYBACK_AUTOPLAY,
                    label=self._lbl_item_autoplay,
                    check=True,
                )
            with dpg.menu(label=self._lbl_group_view):
                self._shortcut_manager.add_menu_item(
                    ShortcutId.TOGGLE_ADVANCED_SETTINGS,
                    tag=TAG_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
                    label=self._lbl_item_show_advanced_settings,
                    check=True,
                )
                self._shortcut_manager.add_menu_item(
                    ShortcutId.TOGGLE_FULLSCREEN,
                    tag=TAG_MENU_ITEM_VIEW_FULLSCREEN,
                    label=self._lbl_item_fullscreen,
                    check=True,
                )

            dpg.add_button(
                label=self._tpl_fps.format(fps=0),
                tag=TAG_TEXT_GLOBAL_MENU_FPS,
                width=-1,
                enabled=False,
            )
            self._fps_theme.bind_to_item(TAG_TEXT_GLOBAL_MENU_FPS)

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
        dpg_configure_item(TAG_TEXT_GLOBAL_MENU_FPS, label=self._tpl_fps.format(fps=fps))
