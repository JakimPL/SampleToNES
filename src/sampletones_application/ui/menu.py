from typing import Final, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    ContextElements,
    GlobalTemplateElements,
    MenuElements,
    PlayerElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.glyphs import PlayerGlyphs
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.tags.general import (
    TAG_GLOBAL_MENU_ITEM_EDIT_REDO,
    TAG_GLOBAL_MENU_ITEM_EDIT_UNDO,
    TAG_GLOBAL_MENU_ITEM_FILE_CLOSE_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_EXPORT_MODULE,
    TAG_GLOBAL_MENU_ITEM_FILE_NEW_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_OPEN_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_PROJECT_PROPERTIES,
    TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT_AS,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_AUTOPLAY,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_FOLLOW,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_LOOP,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_ADD_TO_SEQUENCER,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_CLOSE,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_WAV,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_LOCATE_AUDIO,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_OPEN,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_OPEN_IN_EXPLORER,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_SAVE,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
    TAG_GLOBAL_MENU_ITEM_VIEW_FULLSCREEN,
    TAG_GLOBAL_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
    TAG_GLOBAL_PANEL_PLAYER,
    TAG_GLOBAL_TEXT_MENU_FPS,
)
from sampletones_application.tags.player import (
    SUF_PLAYER_PAUSE,
    SUF_PLAYER_PLAY,
    SUF_PLAYER_STOP,
    SUF_PLAYER_TOOLTIP,
)
from sampletones_application.ui.panels.player.controls import (
    create_compact_transport_controls,
)
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_set_item_label,
    dpg_set_value,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_shared.types.callback import VoidCallback

PROJECT_ITEM_TAGS: Final[Tuple[str, ...]] = (
    TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT_AS,
    TAG_GLOBAL_MENU_ITEM_FILE_PROJECT_PROPERTIES,
    TAG_GLOBAL_MENU_ITEM_FILE_EXPORT_MODULE,
    TAG_GLOBAL_MENU_ITEM_FILE_CLOSE_PROJECT,
)
RECONSTRUCTION_ITEM_TAGS: Final[Tuple[str, ...]] = (
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_CLOSE,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_WAV,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS,
)


class MenuBar:
    def __init__(
        self,
        *,
        shortcut_manager: ShortcutManager,
        fps_theme: Theme,
        player_toolbar_theme: Theme,
        player_glyphs: PlayerGlyphs,
        player_layout: PlayerLayout,
        language_manager: LanguageManager,
        on_play_from_start: VoidCallback,
        on_pause_or_resume: VoidCallback,
        on_stop: VoidCallback,
    ) -> None:
        self._shortcut_manager = shortcut_manager
        self._fps_theme = fps_theme
        self._player_toolbar_theme = player_toolbar_theme
        self._player_glyphs = player_glyphs
        self._player_layout = player_layout
        self._language_manager = language_manager
        self._on_play_from_start = on_play_from_start
        self._on_pause_or_resume = on_pause_or_resume
        self._on_stop = on_stop
        self._tpl_fps = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.FPS,
        ]

        self._play_button_tag = f"{TAG_GLOBAL_PANEL_PLAYER}{SUF_PLAYER_PLAY}"
        self._pause_button_tag = f"{TAG_GLOBAL_PANEL_PLAYER}{SUF_PLAYER_PAUSE}"
        self._stop_button_tag = f"{TAG_GLOBAL_PANEL_PLAYER}{SUF_PLAYER_STOP}"
        self._pause_tooltip_tag = f"{self._pause_button_tag}{SUF_PLAYER_TOOLTIP}"
        self._lbl_play = language_manager[Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.PLAY]
        self._lbl_pause = language_manager[Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.PAUSE]
        self._lbl_resume = language_manager[Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.RESUME]
        self._lbl_stop = language_manager[Page.GLOBAL, Panel.PLAYER, TextType.LABEL, PlayerElements.STOP]

    def _label(self, element: MenuElements) -> str:
        return self._language_manager[Page.GLOBAL, Panel.MENU, TextType.LABEL, element]

    def _context_label(self, element: ContextElements) -> str:
        """Resolves a shared context-action label reused between the tree menus and this bar."""
        return self._language_manager[Page.GLOBAL, Panel.CONTEXT, TextType.LABEL, element]

    def create(self, state: MenuBarViewModel) -> None:
        with dpg.menu_bar():
            self._create_file_menu(state)
            self._create_edit_menu(state)
            self._create_reconstruction_menu(state)
            self._create_playback_menu(state)
            self._create_view_menu()
            self._create_help_menu()
            self._create_player_toolbar()
            self._create_fps_indicator()

    def _create_file_menu(self, state: MenuBarViewModel) -> None:
        with dpg.menu(label=self._label(MenuElements.GROUP_FILE)):
            self._shortcut_manager.add_menu_item(
                ShortcutId.NEW_PROJECT,
                tag=TAG_GLOBAL_MENU_ITEM_FILE_NEW_PROJECT,
                label=self._label(MenuElements.ITEM_FILE_NEW_PROJECT),
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.OPEN_PROJECT,
                tag=TAG_GLOBAL_MENU_ITEM_FILE_OPEN_PROJECT,
                label=self._label(MenuElements.ITEM_FILE_OPEN_PROJECT),
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.SAVE_PROJECT,
                tag=TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT,
                label=self._label(MenuElements.ITEM_FILE_SAVE_PROJECT),
                enabled=state.project_open,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.SAVE_PROJECT_AS,
                tag=TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT_AS,
                label=self._label(MenuElements.ITEM_FILE_SAVE_PROJECT_AS),
                enabled=state.project_open,
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.PROJECT_PROPERTIES,
                tag=TAG_GLOBAL_MENU_ITEM_FILE_PROJECT_PROPERTIES,
                label=self._label(MenuElements.ITEM_FILE_PROJECT_PROPERTIES),
                enabled=state.project_open,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.EXPORT_PROJECT_MODULE,
                tag=TAG_GLOBAL_MENU_ITEM_FILE_EXPORT_MODULE,
                label=self._label(MenuElements.ITEM_FILE_EXPORT_MODULE),
                enabled=state.project_open,
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.CLOSE_PROJECT,
                tag=TAG_GLOBAL_MENU_ITEM_FILE_CLOSE_PROJECT,
                label=self._label(MenuElements.ITEM_FILE_CLOSE_PROJECT),
                enabled=state.project_open,
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.EXIT,
                label=self._label(MenuElements.ITEM_FILE_EXIT),
            )

    def _create_edit_menu(self, state: MenuBarViewModel) -> None:
        with dpg.menu(label=self._label(MenuElements.GROUP_EDIT)):
            self._shortcut_manager.add_menu_item(
                ShortcutId.UNDO,
                tag=TAG_GLOBAL_MENU_ITEM_EDIT_UNDO,
                label=self._label(MenuElements.ITEM_EDIT_UNDO),
                enabled=state.undo_enabled,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.REDO,
                tag=TAG_GLOBAL_MENU_ITEM_EDIT_REDO,
                label=self._label(MenuElements.ITEM_EDIT_REDO),
                enabled=state.redo_enabled,
            )

    def _create_reconstruction_menu(self, state: MenuBarViewModel) -> None:
        with dpg.menu(label=self._label(MenuElements.GROUP_RECONSTRUCTION)):
            self._shortcut_manager.add_menu_item(
                ShortcutId.RECONSTRUCT_FILE,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_FILE,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_RECONSTRUCT_FILE),
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.RECONSTRUCT_DIRECTORY,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_RECONSTRUCT_DIRECTORY),
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.LOAD_GENERATION_SETTINGS,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_LOAD_GENERATION_SETTINGS),
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.SAVE_GENERATION_SETTINGS,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_SAVE_GENERATION_SETTINGS),
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.OPEN_RECONSTRUCTION,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_OPEN,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_OPEN),
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.SAVE_RECONSTRUCTION,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_SAVE,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_SAVE),
                enabled=state.reconstruction_saveable,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.SAVE_RECONSTRUCTION_AS,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_SAVE_AS),
                enabled=state.reconstruction_loaded,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.CLOSE_RECONSTRUCTION,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_CLOSE,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_CLOSE),
                enabled=state.reconstruction_loaded,
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.ADD_RECONSTRUCTION_TO_SEQUENCER,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_ADD_TO_SEQUENCER,
                label=self._context_label(ContextElements.ADD_TO_SEQUENCER),
                enabled=state.add_to_sequencer_enabled,
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.OPEN_RECONSTRUCTION_IN_EXPLORER,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_OPEN_IN_EXPLORER,
                label=self._context_label(ContextElements.OPEN_IN_EXPLORER),
                enabled=state.open_in_explorer_enabled,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.LOCATE_ORIGINAL_AUDIO,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_LOCATE_AUDIO,
                label=self._context_label(ContextElements.LOCATE_ORIGINAL_AUDIO),
                enabled=state.locate_audio_enabled,
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.EXPORT_RECONSTRUCTION_WAV,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_WAV,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_EXPORT_WAV),
                enabled=state.reconstruction_loaded,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.EXPORT_RECONSTRUCTION_INSTRUMENTS,
                tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS,
                label=self._label(MenuElements.ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS),
                enabled=state.reconstruction_loaded,
            )

    def _create_playback_menu(self, state: MenuBarViewModel) -> None:
        with dpg.menu(label=self._label(MenuElements.GROUP_PLAYBACK)):
            self._shortcut_manager.add_menu_item(
                ShortcutId.PLAY,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY,
                label=state.play_label,
                enabled=state.play_or_pause_enabled,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.PLAY_FROM_START,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
                label=self._label(MenuElements.ITEM_PLAYBACK_PLAY_FROM_START),
                enabled=state.play_or_pause_enabled,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.STOP,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP,
                label=self._label(MenuElements.ITEM_PLAYBACK_STOP),
                enabled=state.stop_enabled,
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.TOGGLE_AUTOPLAY,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_AUTOPLAY,
                label=self._label(MenuElements.ITEM_PLAYBACK_AUTOPLAY),
                check=True,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.TOGGLE_FOLLOW_PLAYBACK,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_FOLLOW,
                label=self._label(MenuElements.ITEM_PLAYBACK_FOLLOW_PLAYBACK),
                check=True,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.TOGGLE_LOOP_SONG,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_LOOP,
                label=self._label(MenuElements.ITEM_PLAYBACK_LOOP_SONG),
                check=True,
            )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.AUDIO_SETTINGS,
                label=self._label(MenuElements.ITEM_PLAYBACK_AUDIO_SETTINGS),
            )

    def _create_view_menu(self) -> None:
        with dpg.menu(label=self._label(MenuElements.GROUP_VIEW)):
            self._shortcut_manager.add_menu_item(
                ShortcutId.TOGGLE_ADVANCED_SETTINGS,
                tag=TAG_GLOBAL_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
                label=self._label(MenuElements.ITEM_VIEW_SHOW_ADVANCED_SETTINGS),
                check=True,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.TOGGLE_FULLSCREEN,
                tag=TAG_GLOBAL_MENU_ITEM_VIEW_FULLSCREEN,
                label=self._label(MenuElements.ITEM_VIEW_FULLSCREEN),
                check=True,
            )

    def _create_help_menu(self) -> None:
        with dpg.menu(label=self._label(MenuElements.GROUP_HELP)):
            self._shortcut_manager.add_menu_item(
                ShortcutId.ABOUT_DIALOG,
                label=self._label(MenuElements.ITEM_HELP_ABOUT),
            )

    def _create_player_toolbar(self) -> None:
        """Builds the transport strip sitting on its own recessed surface beside the menus."""
        with dpg.child_window(
            tag=TAG_GLOBAL_PANEL_PLAYER,
            auto_resize_x=True,
            auto_resize_y=True,
            border=True,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        ):
            create_compact_transport_controls(
                TAG_GLOBAL_PANEL_PLAYER,
                layout=self._player_layout,
                glyphs=self._player_glyphs,
                play_tag=self._play_button_tag,
                pause_tag=self._pause_button_tag,
                stop_tag=self._stop_button_tag,
                play_tooltip=self._lbl_play,
                pause_tooltip=self._lbl_pause,
                stop_tooltip=self._lbl_stop,
                on_play=self._on_play_from_start,
                on_pause_or_resume=self._on_pause_or_resume,
                on_stop=self._on_stop,
            )

        self._player_toolbar_theme.bind_to_item(TAG_GLOBAL_PANEL_PLAYER)

    def _create_fps_indicator(self) -> None:
        dpg.add_button(
            label=self._tpl_fps.format(fps=0),
            tag=TAG_GLOBAL_TEXT_MENU_FPS,
            width=-1,
            enabled=False,
        )
        self._fps_theme.bind_to_item(TAG_GLOBAL_TEXT_MENU_FPS)

    def update(self, state: MenuBarViewModel) -> None:
        for project_item_tag in PROJECT_ITEM_TAGS:
            dpg_configure_item(project_item_tag, enabled=state.project_open)

        dpg_configure_item(TAG_GLOBAL_MENU_ITEM_EDIT_UNDO, enabled=state.undo_enabled)
        dpg_configure_item(TAG_GLOBAL_MENU_ITEM_EDIT_REDO, enabled=state.redo_enabled)

        dpg_configure_item(TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_SAVE, enabled=state.reconstruction_saveable)

        for reconstruction_item_tag in RECONSTRUCTION_ITEM_TAGS:
            dpg_configure_item(reconstruction_item_tag, enabled=state.reconstruction_loaded)

        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_ADD_TO_SEQUENCER,
            enabled=state.add_to_sequencer_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_OPEN_IN_EXPLORER,
            enabled=state.open_in_explorer_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_LOCATE_AUDIO,
            enabled=state.locate_audio_enabled,
        )

        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY,
            label=state.play_label,
            enabled=state.play_or_pause_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
            enabled=state.play_or_pause_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP,
            enabled=state.stop_enabled,
        )
        self._update_player_toolbar(state)

        dpg_set_value(TAG_GLOBAL_MENU_ITEM_PLAYBACK_AUTOPLAY, state.autoplay)
        dpg_set_value(TAG_GLOBAL_MENU_ITEM_PLAYBACK_FOLLOW, state.follow_playback)
        dpg_set_value(TAG_GLOBAL_MENU_ITEM_PLAYBACK_LOOP, state.loop_song)
        dpg_set_value(TAG_GLOBAL_MENU_ITEM_VIEW_FULLSCREEN, state.fullscreen)
        dpg_set_value(TAG_GLOBAL_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS, state.advanced_settings)

    def _update_player_toolbar(self, state: MenuBarViewModel) -> None:
        dpg_configure_item(self._play_button_tag, enabled=state.play_or_pause_enabled)
        dpg_configure_item(self._pause_button_tag, enabled=state.pause_enabled)
        dpg_configure_item(self._stop_button_tag, enabled=state.stop_enabled)

        if state.player_paused:
            dpg_set_item_label(self._pause_button_tag, self._player_glyphs.play)
            dpg_set_value(self._pause_tooltip_tag, self._lbl_resume)
        else:
            dpg_set_item_label(self._pause_button_tag, self._player_glyphs.pause)
            dpg_set_value(self._pause_tooltip_tag, self._lbl_pause)

    def update_fps(self, fps: float) -> None:
        dpg_configure_item(
            TAG_GLOBAL_TEXT_MENU_FPS,
            label=self._tpl_fps.format(fps=fps),
        )
