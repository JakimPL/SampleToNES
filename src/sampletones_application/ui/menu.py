from functools import partial
from typing import Callable, Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import context_label
from sampletones_application.categories.elements.global_ import (
    ContextElements,
    MenuElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.trackers import (
    TRACKER_PROJECT_MENU_LABELS,
    TRACKER_SAMPLE_MENU_LABELS,
)
from sampletones_application.constants.playback import FollowMode
from sampletones_application.layout.glyphs.player import PlayerGlyphs
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HANDLER_REGISTRY,
    TAG_GLOBAL_MENU_GROUP_EDIT,
    TAG_GLOBAL_MENU_GROUP_EDIT_MARKER,
    TAG_GLOBAL_MENU_ITEM_EDIT_REDO,
    TAG_GLOBAL_MENU_ITEM_EDIT_UNDO,
    TAG_GLOBAL_MENU_ITEM_FILE_CLOSE_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_EXPORT,
    TAG_GLOBAL_MENU_ITEM_FILE_NEW_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_OPEN_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_PROJECT_PROPERTIES,
    TAG_GLOBAL_MENU_ITEM_FILE_RENDER_SONG,
    TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT_AS,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_AUTOPLAY,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_CHANNELS,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_FOLLOW,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_LOOP_SONG,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY_FROM_FRAME,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY_FROM_START,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP,
    TAG_GLOBAL_MENU_ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS,
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
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.panels.player.controls import (
    create_compact_transport_controls,
)
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.dpg import (
    dpg_append_items,
    dpg_configure_item,
    dpg_delete_item,
    dpg_set_item_label,
    dpg_set_value,
)
from sampletones_application.utils.gui.shortcuts.ids import (
    CHANNEL_SHORTCUT_IDS,
    FOLLOW_MODE_SHORTCUT_IDS,
    PROJECT_EXPORT_SHORTCUT_IDS,
    SAMPLE_EXPORT_SHORTCUT_IDS,
    ShortcutId,
)
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.shared.menu import MenuBarViewModel
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

PROJECT_ITEM_TAGS: Final[Tuple[str, ...]] = (
    TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT,
    TAG_GLOBAL_MENU_ITEM_FILE_SAVE_PROJECT_AS,
    TAG_GLOBAL_MENU_ITEM_FILE_PROJECT_PROPERTIES,
    TAG_GLOBAL_MENU_ITEM_FILE_EXPORT,
    TAG_GLOBAL_MENU_ITEM_FILE_CLOSE_PROJECT,
)
RECONSTRUCTION_ITEM_TAGS: Final[Tuple[str, ...]] = (
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_SAVE_AS,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_CLOSE,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_WAV,
    TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS,
)
FOLLOW_MODE_LABELS: Final[Dict[FollowMode, MenuElements]] = {
    FollowMode.ROWS: MenuElements.ITEM_PLAYBACK_FOLLOW_ROWS,
    FollowMode.PATTERNS: MenuElements.ITEM_PLAYBACK_FOLLOW_PATTERNS,
    FollowMode.OFF: MenuElements.ITEM_PLAYBACK_FOLLOW_OFF,
}
UNFOCUSED_CLIPBOARD_ELEMENTS: Final[Tuple[ContextElements, ...]] = (
    ContextElements.COPY,
    ContextElements.CUT,
    ContextElements.PASTE,
    ContextElements.DELETE,
)
CHANNEL_LABELS: Final[Dict[GeneratorName, ContextElements]] = {
    GeneratorName.PULSE1: ContextElements.PULSE_1,
    GeneratorName.PULSE2: ContextElements.PULSE_2,
    GeneratorName.TRIANGLE: ContextElements.TRIANGLE,
    GeneratorName.NOISE: ContextElements.NOISE,
}


class MenuBar:
    def __init__(
        self,
        *,
        shortcut_manager: ShortcutManager,
        fps_theme: Theme,
        player_toolbar_theme: Theme,
        player_button_theme: Theme,
        player_glyphs: PlayerGlyphs,
        player_layout: PlayerLayout,
        language_manager: LanguageManager,
        build_edit_actions: Callable[[], bool],
        on_play_from_start: VoidCallback,
        on_pause_or_resume: VoidCallback,
        on_stop: VoidCallback,
        on_channel_muted: Callable[[GeneratorName], None],
    ) -> None:
        self._shortcut_manager = shortcut_manager
        self._fps_theme = fps_theme
        self._player_toolbar_theme = player_toolbar_theme
        self._player_button_theme = player_button_theme
        self._player_glyphs = player_glyphs
        self._player_layout = player_layout
        self._language_manager = language_manager
        self._build_edit_actions = build_edit_actions
        self._on_play_from_start = on_play_from_start
        self._on_pause_or_resume = on_pause_or_resume
        self._on_stop = on_stop
        self._on_channel_muted = on_channel_muted
        self._tpl_fps = language_manager["global.dialog.template.fps"]

        self._play_button_tag = compose_tag(TAG_GLOBAL_PANEL_PLAYER, SUF_PLAYER_PLAY)
        self._pause_button_tag = compose_tag(TAG_GLOBAL_PANEL_PLAYER, SUF_PLAYER_PAUSE)
        self._stop_button_tag = compose_tag(TAG_GLOBAL_PANEL_PLAYER, SUF_PLAYER_STOP)
        self._pause_tooltip_tag = compose_tag(self._pause_button_tag, SUF_PLAYER_TOOLTIP)
        self._lbl_pause = language_manager["global.player.label.pause"]

        self._edit_actions_handler_tag = compose_tag(
            TAG_GLOBAL_MENU_GROUP_EDIT_MARKER,
            SUF_HANDLER_REGISTRY,
        )
        self._edit_actions_frame: Optional[int] = None
        self._edit_action_items: Tuple[Sender, ...] = ()

    def _label(self, element: MenuElements) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.MENU,
            TextType.LABEL,
            element,
        ]

    def _context_label(self, element: ContextElements) -> str:
        return context_label(self._language_manager, element)

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
            self._create_project_export_menu(state)
            self._shortcut_manager.add_menu_item(
                ShortcutId.RENDER_SONG,
                tag=TAG_GLOBAL_MENU_ITEM_FILE_RENDER_SONG,
                label=self._label(MenuElements.ITEM_FILE_RENDER_SONG),
                enabled=state.render_enabled,
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

    def _create_project_export_menu(self, state: MenuBarViewModel) -> None:
        """Builds the submenu that writes the open project for one tracker.

        Each format reads its own kind of file, so the formats are listed side by side and
        the one chosen decides what the destination dialog offers. The submenu is open while
        a project is, which is where the whole group takes its enabled state.
        """
        with dpg.menu(
            tag=TAG_GLOBAL_MENU_ITEM_FILE_EXPORT,
            label=self._label(MenuElements.GROUP_FILE_EXPORT),
            enabled=state.project_open,
        ):
            for tracker_format, shortcut_id in PROJECT_EXPORT_SHORTCUT_IDS.items():
                self._shortcut_manager.add_menu_item(
                    shortcut_id,
                    label=self._label(TRACKER_PROJECT_MENU_LABELS[tracker_format]),
                )

    def _create_edit_menu(self, state: MenuBarViewModel) -> None:
        """Builds the Edit menu: the history steps, then the actions of whoever holds the cursor.

        The actions are stated into the menu itself and taken away again on each opening, so they
        follow the cursor. A marker leads the menu, holding nothing and reporting the popup drawn:
        a container standing below a menu item takes the width those items span as its own, which
        the popup then grows to fit on every frame it stays open.
        """
        with dpg.menu(
            label=self._label(MenuElements.GROUP_EDIT),
            tag=TAG_GLOBAL_MENU_GROUP_EDIT,
        ):
            dpg.add_group(tag=TAG_GLOBAL_MENU_GROUP_EDIT_MARKER)
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
            dpg.add_separator()

        with dpg.item_handler_registry(tag=self._edit_actions_handler_tag):
            dpg.add_item_visible_handler(callback=self._on_edit_actions_drawn)

        dpg.bind_item_handler_registry(
            TAG_GLOBAL_MENU_GROUP_EDIT_MARKER,
            self._edit_actions_handler_tag,
        )
        self._refresh_edit_actions()

    def _on_edit_actions_drawn(
        self,
        _sender: Sender,
        _app_data: Sender,
    ) -> None:
        """States the actions afresh each time the Edit menu is opened.

        DearPyGui reports the marker drawn once a frame while the menu stands open, so a gap in
        those reports marks a fresh opening. The actions stay standing between openings, which
        gives the popup its full height on the frame it appears, and the rebuilt ones take over a
        frame later — long before an item can be reached and chosen.
        """
        frame = dpg.get_frame_count()
        reopened = self._edit_actions_frame is None or frame - self._edit_actions_frame > 1
        self._edit_actions_frame = frame
        if reopened:
            self._refresh_edit_actions()

    def _refresh_edit_actions(self) -> None:
        """Takes the standing actions out of the Edit menu and asks the focused surface for its own.

        A surface builds the same actions its own cell menu offers, so the two doors print one set
        with the keys and the enablement each action carries. The history steps above them stand
        where they are, since only what the last build stated is taken away.
        """
        for item in self._edit_action_items:
            dpg_delete_item(item)

        self._edit_action_items = dpg_append_items(
            TAG_GLOBAL_MENU_GROUP_EDIT,
            self._add_edit_action_items,
        )

    def _add_edit_action_items(self) -> None:
        """States the focused surface's actions, or the clipboard four greyed out while none is."""
        if not self._build_edit_actions():
            self._add_unfocused_clipboard_items()

    def _add_unfocused_clipboard_items(self) -> None:
        """Names the clipboard actions greyed out, the Edit menu with no grid holding a cursor."""
        for element in UNFOCUSED_CLIPBOARD_ELEMENTS:
            dpg.add_menu_item(
                label=self._context_label(element),
                enabled=False,
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
            self._create_instruments_export_menu(state)

    def _create_instruments_export_menu(self, state: MenuBarViewModel) -> None:
        """Builds the submenu that writes the loaded reconstruction's slices for one tracker.

        Each format able to write a file per slice gets its own item, so choosing the tracker
        is one click and the destination dialog then offers that tracker's file type alone.
        """
        with dpg.menu(
            tag=TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_EXPORT_INSTRUMENTS,
            label=self._label(MenuElements.GROUP_RECONSTRUCTION_EXPORT_INSTRUMENTS),
            enabled=state.reconstruction_loaded,
        ):
            for tracker_format, shortcut_id in SAMPLE_EXPORT_SHORTCUT_IDS.items():
                self._shortcut_manager.add_menu_item(
                    shortcut_id,
                    label=self._label(TRACKER_SAMPLE_MENU_LABELS[tracker_format]),
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
                enabled=state.play_from_start_enabled,
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.PLAY_FROM_FRAME,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY_FROM_FRAME,
                label=self._label(MenuElements.ITEM_PLAYBACK_PLAY_FROM_FRAME),
                enabled=state.play_from_frame_enabled,
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
            self._create_follow_menu(state)
            self._shortcut_manager.add_menu_item(
                ShortcutId.TOGGLE_LOOP_SONG,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_LOOP_SONG,
                label=self._label(MenuElements.ITEM_PLAYBACK_LOOP_SONG),
                check=True,
            )
            self._create_channels_menu(state)
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.AUDIO_SETTINGS,
                label=self._label(MenuElements.ITEM_PLAYBACK_AUDIO_SETTINGS),
            )

    def _create_follow_menu(self, state: MenuBarViewModel) -> None:
        """Builds the submenu that chooses how far the sequencer view chases the playhead.

        The modes stand as one choice, so the check marks the reach in place and choosing another
        item moves it there. Each mode carries its own key, which is what lets a reader switch
        reach mid-playback straight from the keyboard.
        """
        with dpg.menu(
            tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_FOLLOW,
            label=self._label(MenuElements.GROUP_PLAYBACK_FOLLOW),
        ):
            for mode, shortcut_id in FOLLOW_MODE_SHORTCUT_IDS.items():
                self._shortcut_manager.add_menu_item(
                    shortcut_id,
                    tag=self._follow_menu_item_tag(mode),
                    label=self._label(FOLLOW_MODE_LABELS[mode]),
                    check=True,
                    default_value=state.follow_mode is mode,
                )

    def _create_channels_menu(self, state: MenuBarViewModel) -> None:
        """Builds the submenu that switches each tracker channel of the sequencer's song.

        A channel carries a check while it sounds, so the submenu reads as the mix the tracker's
        columns and the order table's rows show, and choosing one silences it. The closing item
        brings the whole mix back in one gesture, and it is offered while a channel is silenced.

        The check names the sequencer's mix, so choosing an item switches that mix wherever the
        reader stands, while the key printed beside it reaches the channels of the tab in front.
        """
        with dpg.menu(
            tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_CHANNELS,
            label=self._label(MenuElements.GROUP_PLAYBACK_CHANNELS),
        ):
            for generator, shortcut_id in CHANNEL_SHORTCUT_IDS.items():
                self._shortcut_manager.add_menu_item(
                    shortcut_id,
                    callback=partial(self._on_channel_muted, generator),
                    tag=self._channel_menu_item_tag(generator),
                    label=self._context_label(CHANNEL_LABELS[generator]),
                    check=True,
                    default_value=not state.channels.is_muted(generator),
                )
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.UNMUTE_ALL_CHANNELS,
                tag=TAG_GLOBAL_MENU_ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS,
                label=self._label(MenuElements.ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS),
                enabled=state.channels.any_muted,
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
            dpg.add_separator()
            self._shortcut_manager.add_menu_item(
                ShortcutId.DISPLAY_SETTINGS,
                label=self._label(MenuElements.ITEM_VIEW_DISPLAY_SETTINGS),
            )
            self._shortcut_manager.add_menu_item(
                ShortcutId.KEYBOARD_SETTINGS,
                label=self._label(MenuElements.ITEM_VIEW_KEYBOARD_SETTINGS),
            )

    def _create_help_menu(self) -> None:
        with dpg.menu(label=self._label(MenuElements.GROUP_HELP)):
            self._shortcut_manager.add_menu_item(
                ShortcutId.ABOUT_DIALOG,
                label=self._label(MenuElements.ITEM_HELP_ABOUT),
            )

    def _create_player_toolbar(self) -> None:
        """Builds the transport strip sitting on its own recessed surface beside the menus."""
        dpg.add_spacer(width=self._player_layout.toolbar.indent)
        with dpg.child_window(
            tag=TAG_GLOBAL_PANEL_PLAYER,
            width=self._player_layout.toolbar.width,
            height=self._player_layout.toolbar.height,
            auto_resize_y=False,
            border=False,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        ):
            create_compact_transport_controls(
                TAG_GLOBAL_PANEL_PLAYER,
                layout=self._player_layout,
                glyphs=self._player_glyphs,
                button_theme=self._player_button_theme,
                play_tag=self._play_button_tag,
                pause_tag=self._pause_button_tag,
                stop_tag=self._stop_button_tag,
                play_tooltip=self._language_manager["global.player.label.play"],
                pause_tooltip=self._lbl_pause,
                stop_tooltip=self._language_manager["global.player.label.stop"],
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
        FontRegistry.bind_to_item(TAG_GLOBAL_TEXT_MENU_FPS, Font.MONO_SMALL)

    def update(self, state: MenuBarViewModel) -> None:
        for project_item_tag in PROJECT_ITEM_TAGS:
            dpg_configure_item(project_item_tag, enabled=state.project_open)

        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_FILE_RENDER_SONG,
            enabled=state.render_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_EDIT_UNDO,
            enabled=state.undo_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_EDIT_REDO,
            enabled=state.redo_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_RECONSTRUCTION_SAVE,
            enabled=state.reconstruction_saveable,
        )

        for reconstruction_item_tag in RECONSTRUCTION_ITEM_TAGS:
            dpg_configure_item(
                reconstruction_item_tag,
                enabled=state.reconstruction_loaded,
            )

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
            enabled=state.play_from_start_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_PLAYBACK_PLAY_FROM_FRAME,
            enabled=state.play_from_frame_enabled,
        )
        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_PLAYBACK_STOP,
            enabled=state.stop_enabled,
        )
        self._update_player_toolbar(state)

        dpg_set_value(TAG_GLOBAL_MENU_ITEM_PLAYBACK_AUTOPLAY, state.autoplay)
        dpg_set_value(TAG_GLOBAL_MENU_ITEM_PLAYBACK_LOOP_SONG, state.loop_song)
        self._update_follow_mode(state)
        self._update_channels(state)
        dpg_set_value(TAG_GLOBAL_MENU_ITEM_VIEW_FULLSCREEN, state.fullscreen)
        dpg_set_value(
            TAG_GLOBAL_MENU_ITEM_VIEW_SHOW_ADVANCED_SETTINGS,
            state.advanced_settings,
        )

    def _update_follow_mode(self, state: MenuBarViewModel) -> None:
        """Marks the reach the view follows the playhead at, the one mode carrying the check."""
        for mode in FOLLOW_MODE_SHORTCUT_IDS:
            dpg_set_value(self._follow_menu_item_tag(mode), state.follow_mode is mode)

    def _update_channels(self, state: MenuBarViewModel) -> None:
        """Shows the mute set the sequencer's tables show: a check on every channel that sounds."""
        for generator in CHANNEL_SHORTCUT_IDS:
            dpg_set_value(self._channel_menu_item_tag(generator), not state.channels.is_muted(generator))

        dpg_configure_item(
            TAG_GLOBAL_MENU_ITEM_PLAYBACK_UNMUTE_ALL_CHANNELS,
            enabled=state.channels.any_muted,
        )

    def _update_player_toolbar(self, state: MenuBarViewModel) -> None:
        dpg_configure_item(
            self._play_button_tag,
            enabled=state.play_from_start_enabled,
        )
        dpg_configure_item(self._pause_button_tag, enabled=state.pause_enabled)
        dpg_configure_item(self._stop_button_tag, enabled=state.stop_enabled)

        if state.player_paused:
            dpg_set_item_label(
                self._pause_button_tag,
                self._player_glyphs.resume,
            )
            dpg_set_value(self._pause_tooltip_tag, self._language_manager["global.player.label.resume"])
        else:
            dpg_set_item_label(
                self._pause_button_tag,
                self._player_glyphs.pause,
            )
            dpg_set_value(self._pause_tooltip_tag, self._lbl_pause)

    def update_fps(self, fps: float) -> None:
        dpg_configure_item(
            TAG_GLOBAL_TEXT_MENU_FPS,
            label=self._tpl_fps.format(fps=fps),
        )

    @staticmethod
    def _channel_menu_item_tag(generator: GeneratorName) -> str:
        """The tag of the Channels submenu item that switches ``generator``."""
        return compose_tag(TAG_GLOBAL_MENU_ITEM_PLAYBACK_CHANNELS, generator.value)

    @staticmethod
    def _follow_menu_item_tag(mode: FollowMode) -> str:
        """The tag of the Follow playback submenu item that chooses ``mode``."""
        return compose_tag(TAG_GLOBAL_MENU_ITEM_PLAYBACK_FOLLOW, mode.value)
