from typing import Callable, Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import (
    SequencerVoicesElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_HANDLER_LIST, SUF_HANDLER_REGISTRY
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_VOICES_BUTTON_NEW_INSTRUMENT,
    TAG_SEQUENCER_VOICES_INPUT_RENAME,
    TAG_SEQUENCER_VOICES_PANEL,
    TAG_SEQUENCER_VOICES_TABLE,
    TAG_SEQUENCER_VOICES_THEME_ROW,
    TAG_SEQUENCER_VOICES_WINDOW,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.panels.sequencer.voices.menu import VoicesMenu
from sampletones_application.ui.panels.sequencer.voices.moves import MOVE_DIRECTIONS
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_delete_children, dpg_pointer_within_window
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.keyboard import (
    PRIORITY_PANEL,
    ActivePredicate,
    KeyEvent,
    KeyRouter,
)
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.view_model.sequencer.voices import (
    SequencerVoicesViewModel,
    VoiceEntryViewModel,
    VoiceKind,
    VoiceSelection,
)
from sampletones_application.view_model.shared.footprint import SampleFootprintViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_id
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import StringCallback, VoidCallback

FROZEN_HEADER_ROWS: Final[int] = 1


class GUISequencerVoicesPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: SequencerLayout,
        detail_color: BaseColor,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        tab_active: ActivePredicate,
        shortcut_source: ShortcutSource,
        initial_collapsed: bool = False,
    ) -> None:
        self._language_manager = language_manager
        self._layout = layout
        self._router = key_router
        self._tab_active = tab_active
        self._shortcuts = shortcut_source
        self._row_handler_tag = compose_tag(TAG_SEQUENCER_VOICES_TABLE, SUF_HANDLER_REGISTRY)
        self._rename_handler_tag = compose_tag(TAG_SEQUENCER_VOICES_INPUT_RENAME, SUF_HANDLER_REGISTRY)
        self._list_handler_tag = compose_tag(TAG_SEQUENCER_VOICES_WINDOW, SUF_HANDLER_LIST)
        self._list_menu_pending = False
        self._selected_voice_id: Optional[str] = None
        self._selected_row: Optional[int] = None
        self._editing_voice_id: Optional[str] = None
        self._entries: Tuple[VoiceEntryViewModel, ...] = ()
        self._tip_new_instrument = self._tooltip(language_manager, SequencerVoicesElements.NEW_INSTRUMENT)
        self._tip_kind_sample = self._tooltip(language_manager, SequencerVoicesElements.KIND_SAMPLE)
        self._tip_kind_instrument = self._tooltip(language_manager, SequencerVoicesElements.KIND_INSTRUMENT)
        self.sample_footprint: Optional[Callable[[str], Optional[SampleFootprintViewModel]]] = None
        self.voice_instruments: Optional[Callable[[str], Tuple[Optional[ChannelName], ...]]] = None
        self.instrument_channels: Optional[Callable[[str], Tuple[ChannelName, ...]]] = None
        self.on_sample_selected: Optional[StringCallback] = None
        self.on_sample_edit_requested: Optional[StringCallback] = None
        self.on_loop_changed: Optional[Callable[[str, bool], None]] = None
        self.on_remove_requested: Optional[StringCallback] = None
        self.on_play_requested: Optional[StringCallback] = None
        self.on_move_requested: Optional[Callable[[str, int], None]] = None
        self.on_rename_committed: Optional[Callable[[str, str], None]] = None
        self.on_duplicate_requested: Optional[StringCallback] = None
        self.on_new_instrument_requested: Optional[VoidCallback] = None
        self.on_add_sample_requested: Optional[VoidCallback] = None
        self.on_import_instrument_requested: Optional[VoidCallback] = None
        self.on_export_instrument_requested: Optional[Callable[[str, Optional[ChannelName]], None]] = None
        self.on_instrument_from_channel_requested: Optional[Callable[[str, ChannelName], None]] = None
        self._menu = VoicesMenu(
            self,
            language_manager=language_manager,
            shortcut_source=shortcut_source,
            detail_color=detail_color,
        )

        super().__init__(
            tag=TAG_SEQUENCER_VOICES_PANEL,
            width=-1,
            height=-layout.history.height,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._label(self._language_manager, SequencerVoicesElements.VOICES_TEXT),
            glyph=self._glyphs.headers.voices,
        ):
            self._create_new_instrument_button()
            self._create_voices_table()

        self._create_row_handlers()
        self._create_list_handler()
        self._create_rename_handler()
        self._create_key_handler()

    def _create_row_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._row_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_sample_clicked)
            dpg.add_item_double_clicked_handler(callback=self._on_sample_double_clicked)

    def _create_list_handler(self) -> None:
        """Answers a press that lands on the list itself rather than on one of its rows."""
        with dpg.handler_registry(tag=self._list_handler_tag):
            dpg.add_mouse_click_handler(
                button=dpg.mvMouseButton_Right,
                callback=self._on_list_right_clicked,
            )

    def _create_rename_handler(self) -> None:
        with dpg.item_handler_registry(tag=self._rename_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_rename_deactivated)

    def _create_key_handler(self) -> None:
        self._router.register(
            self._on_key_pressed,
            priority=PRIORITY_PANEL,
            active=self._keys_active,
        )

    def _create_new_instrument_button(self) -> None:
        """Offers a hand-written voice, which is the one kind no browser brings in."""
        button = dpg.add_button(
            tag=TAG_SEQUENCER_VOICES_BUTTON_NEW_INSTRUMENT,
            label=self._label(self._language_manager, SequencerVoicesElements.NEW_INSTRUMENT),
            width=-1,
            callback=lambda: self.call(self.on_new_instrument_requested),
        )
        FontRegistry.bind_to_item(button, Font.REGULAR_SMALL)
        show_tooltip(button, self._tip_new_instrument)

    def _create_voices_table(self) -> None:
        with (
            dpg.child_window(
                tag=TAG_SEQUENCER_VOICES_WINDOW,
                border=False,
                width=-1,
                height=-1,
            ),
            dpg.table(
                tag=TAG_SEQUENCER_VOICES_TABLE,
                width=-1,
                height=-1,
                header_row=True,
                resizable=False,
                borders_innerH=False,
                borders_innerV=True,
                borders_outerH=True,
                borders_outerV=True,
                scrollY=True,
                freeze_rows=FROZEN_HEADER_ROWS,
                row_background=True,
                policy=dpg.mvTable_SizingFixedFit,
            ),
        ):
            dpg.add_table_column(
                label=self._label(
                    self._language_manager,
                    SequencerVoicesElements.COLUMN_KIND,
                ),
                width_fixed=True,
                init_width_or_weight=self._layout.table_cells.voice.kind,
            )
            dpg.add_table_column(
                label=self._label(
                    self._language_manager,
                    SequencerVoicesElements.COLUMN_ID,
                ),
                width_fixed=True,
                init_width_or_weight=self._layout.table_cells.voice.id,
            )
            dpg.add_table_column(
                label=self._label(
                    self._language_manager,
                    SequencerVoicesElements.COLUMN_NAME,
                ),
                width_stretch=True,
                init_width_or_weight=self._layout.table_cells.voice.name,
            )
            dpg.add_table_column(
                label=self._label(
                    self._language_manager,
                    SequencerVoicesElements.COLUMN_LOOP,
                ),
                width_fixed=True,
                init_width_or_weight=self._layout.table_cells.voice.loop,
            )
        ThemeRegistry.get(TAG_SEQUENCER_VOICES_THEME_ROW).bind_to_item(TAG_SEQUENCER_VOICES_TABLE)

    def update_view(self, view_model: SequencerVoicesViewModel) -> None:
        self._entries = view_model.voices
        self._editing_voice_id = None
        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuilds the samples table from the cached entries with explicit parents.

        Items pass an explicit ``parent`` so each widget binds directly: the browser
        tree builds on a worker thread and the DearPyGui container stack is
        process-global, so explicit parents keep this build independent of that
        shared stack.
        """
        dpg_delete_children(TAG_SEQUENCER_VOICES_TABLE, slot=1)
        self._selected_row = None
        for position, entry in enumerate(self._entries):
            self._build_sample_row(position, entry)
        if self._selected_row is None:
            self._selected_voice_id = None

    def _build_sample_row(
        self,
        position: int,
        entry: VoiceEntryViewModel,
    ) -> None:
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_VOICES_TABLE)
        self._build_kind_cell(row_id, entry)
        self._build_id_cell(row_id, position, entry)
        self._build_name_cell(row_id, position, entry)
        self._build_loop_cell(row_id, entry)
        if entry.voice_id == self._selected_voice_id:
            self._selected_row = position
            self._highlight_selected_row(position)

    def _highlight_selected_row(self, position: int) -> None:
        dpg.highlight_table_row(
            TAG_SEQUENCER_VOICES_TABLE,
            position,
            color=self._layout.colors.cell_cursor.rgba,
        )

    def repaint(self) -> None:
        """Issues the selected row's tint again so it takes the palette now in place.

        DearPyGui keeps a row highlight on the table rather than on an item, so the colour
        reaches it only by being pushed again.
        """
        if self._selected_row is None or not dpg.does_item_exist(TAG_SEQUENCER_VOICES_TABLE):
            return

        self._highlight_selected_row(self._selected_row)

    def _build_kind_cell(
        self,
        row_id: int | str,
        entry: VoiceEntryViewModel,
    ) -> None:
        """Marks which kind the row carries, so a converted voice reads apart from a written one.

        The glyph names the kind and its colour repeats it, which is the same pair the tracker's
        voice slot wears — so a row and the cells naming it read as one thing across the two panels.
        """
        kind_cell = dpg.add_table_cell(parent=row_id)
        mark = dpg.add_text(
            parent=kind_cell,
            default_value=self._kind_glyph(entry.kind),
        )
        FontRegistry.bind_to_item(mark, Font.ICON)
        dpg_set_palette_color(mark, self._kind_color(entry.kind))
        show_tooltip(mark, self._kind_tooltip(entry.kind))

    def _kind_glyph(self, kind: VoiceKind) -> str:
        match kind:
            case VoiceKind.SAMPLE:
                return self._glyphs.voices.sample
            case VoiceKind.INSTRUMENT:
                return self._glyphs.voices.instrument

    def _kind_color(self, kind: VoiceKind) -> BaseColor:
        text = self._layout.colors.text
        match kind:
            case VoiceKind.SAMPLE:
                return text.sample
            case VoiceKind.INSTRUMENT:
                return text.instrument

    def _kind_tooltip(self, kind: VoiceKind) -> str:
        match kind:
            case VoiceKind.SAMPLE:
                return self._tip_kind_sample
            case VoiceKind.INSTRUMENT:
                return self._tip_kind_instrument

    def _build_id_cell(
        self,
        row_id: int | str,
        position: int,
        entry: VoiceEntryViewModel,
    ) -> None:
        id_cell = dpg.add_table_cell(parent=row_id)
        id_selectable = dpg.add_selectable(
            parent=id_cell,
            label=display_id(position),
            user_data=(position, entry.voice_id),
            callback=self._on_sample_selected,
        )
        FontRegistry.bind_to_item(id_selectable, Font.MONO_SMALL)
        dpg.bind_item_handler_registry(id_selectable, self._row_handler_tag)

    def _build_name_cell(
        self,
        row_id: int | str,
        position: int,
        entry: VoiceEntryViewModel,
    ) -> None:
        name_cell = dpg.add_table_cell(parent=row_id)
        if entry.voice_id == self._editing_voice_id:
            self._build_name_input(name_cell, entry)
        else:
            self._build_name_selectable(name_cell, position, entry)

    def _build_name_selectable(
        self,
        name_cell: int | str,
        position: int,
        entry: VoiceEntryViewModel,
    ) -> None:
        name_selectable = dpg.add_selectable(
            parent=name_cell,
            label=entry.name,
            user_data=(position, entry.voice_id),
            callback=self._on_sample_selected,
        )
        FontRegistry.bind_to_item(name_selectable, Font.MONO_SMALL)
        dpg.bind_item_handler_registry(name_selectable, self._row_handler_tag)

    def _build_name_input(
        self,
        name_cell: int | str,
        entry: VoiceEntryViewModel,
    ) -> None:
        name_input = dpg.add_input_text(
            tag=TAG_SEQUENCER_VOICES_INPUT_RENAME,
            parent=name_cell,
            default_value=entry.name,
            width=-1,
            on_enter=True,
            callback=self._on_rename_enter,
        )
        FontRegistry.bind_to_item(name_input, Font.MONO_SMALL)
        dpg.bind_item_handler_registry(name_input, self._rename_handler_tag)

    def _build_loop_cell(
        self,
        row_id: int | str,
        entry: VoiceEntryViewModel,
    ) -> None:
        loop_cell = dpg.add_table_cell(parent=row_id)
        loop_checkbox = dpg.add_checkbox(
            parent=loop_cell,
            default_value=entry.loop,
            user_data=entry.voice_id,
            callback=self._on_loop_toggled,
        )
        FontRegistry.bind_to_item(loop_checkbox, Font.REGULAR_SMALL)

    def _on_sample_selected(
        self,
        sender: Sender,
        _app_data: bool,
        user_data: Tuple[int, str],
    ) -> None:
        position, voice_id = user_data
        dpg.set_value(sender, False)
        if self._selected_row is not None:
            dpg.unhighlight_table_row(
                TAG_SEQUENCER_VOICES_TABLE,
                self._selected_row,
            )

        self._selected_row = position
        self._selected_voice_id = voice_id
        self._highlight_selected_row(position)
        self.call(self.on_sample_selected, voice_id)

    @property
    def selection(self) -> Optional[VoiceSelection]:
        """The selected sample, or ``None`` while the panel holds no selection.

        Derived from the highlighted row and the cached entries on each read, so it reports
        whatever the table currently shows. Lets an operation hosted by another panel of the tab
        address the selection without keeping a copy of it.
        """
        if self._selected_voice_id is None or self._selected_row is None:
            return None

        entry = self._entry_for(self._selected_voice_id)
        if entry is None:
            return None

        return VoiceSelection(
            voice_id=entry.voice_id,
            position=self._selected_row,
            name=entry.name,
            kind=entry.kind,
        )

    def deselect(self) -> None:
        """Drops the sample selection so the panel stops consuming keystrokes.

        Mirrors the grid and order panels: each registers a key-router scope that is active only
        while it holds a selection, so a single selection across the three decides which one acts
        on a keystroke. Selecting a cell in another panel clears this one's selection via this method.
        """
        if self._selected_row is not None:
            dpg.unhighlight_table_row(
                TAG_SEQUENCER_VOICES_TABLE,
                self._selected_row,
            )

        self._selected_row = None
        self._selected_voice_id = None

    def _keys_active(self) -> bool:
        """Whether the samples panel owns the next key.

        The panel answers only while its tab is in front, since a selection outlives a move to
        another tab. There, a name being edited keeps the keyboard so Escape can cancel the rename;
        otherwise the panel acts when a sample is selected and no field holds the keyboard. A modal
        dialog claims keys at a higher priority in the router, so the panel needs no modal check.
        """
        if not self._tab_active():
            return False

        if self._editing_voice_id is not None:
            return True

        return self._selected_voice_id is not None and not self._router.is_field_focused

    def _on_key_pressed(self, event: KeyEvent) -> bool:
        """Applies a samples key to the selected sample, reporting whether the panel consumed it.

        The scheme says which press each samples action answers to; a press the samples category
        leaves unnamed goes to the application's global shortcuts.
        """
        shortcut_id = self._shortcuts.action(ShortcutCategory.VOICES, event)
        if self._editing_voice_id is not None:
            return self._cancel_edit(shortcut_id)

        voice_id = self._selected_voice_id
        if voice_id is None or shortcut_id is None:
            return False

        if self._move_voice(shortcut_id):
            return True

        match shortcut_id:
            case ShortcutId.VOICES_REMOVE_VOICE:
                self.call(self.on_remove_requested, voice_id)
            case ShortcutId.VOICES_RENAME_VOICE:
                self.start_rename(voice_id)
            case _:
                return False

        return True

    def _cancel_edit(self, shortcut_id: Optional[ShortcutId]) -> bool:
        """Drops the name being edited, reporting whether the press was the cancel.

        A rename in progress keeps every other key for the input, so typing a name reaches the
        field rather than the panel.
        """
        if shortcut_id is not ShortcutId.VOICES_CANCEL_RENAME:
            return False

        self._cancel_rename()
        return True

    def _move_voice(self, shortcut_id: ShortcutId) -> bool:
        """Moves the selected sample up, down, to the top or to the bottom of the list.

        Returns whether the action was one of the moves, so a boundary with nowhere to go still
        counts as consumed and stays out of the global shortcuts.
        """
        direction = MOVE_DIRECTIONS.get(shortcut_id)
        if direction is None or self._selected_voice_id is None or self._selected_row is None:
            return False

        target = direction.target(self._selected_row, len(self._entries))
        if target is not None:
            self.call(self.on_move_requested, self._selected_voice_id, target)

        return True

    def start_rename(self, voice_id: str) -> None:
        """Turns the sample's name cell into a focused text input."""
        if self._entry_for(voice_id) is None:
            return

        self._editing_voice_id = voice_id
        self._rebuild()
        FrameCallbackManager.set_frame_callback(lambda: dpg.focus_item(TAG_SEQUENCER_VOICES_INPUT_RENAME))

    def _commit_rename(self) -> None:
        """Applies the edited name and restores the read-only cell.

        Clears the edit before notifying so the input's deactivated handler, fired
        during the teardown rebuild, sees the edit already finished.
        """
        if self._editing_voice_id is None:
            return

        voice_id = self._editing_voice_id
        name = dpg.get_value(TAG_SEQUENCER_VOICES_INPUT_RENAME)
        self._editing_voice_id = None
        self.call(self.on_rename_committed, voice_id, name)
        self._rebuild()

    def _cancel_rename(self) -> None:
        if self._editing_voice_id is None:
            return

        self._editing_voice_id = None
        self._rebuild()

    def _on_rename_enter(self, _sender: Sender, _app_data: str) -> None:
        self._commit_rename()

    def _on_rename_deactivated(self, _sender: Sender, _app_data: int) -> None:
        self._commit_rename()

    def _on_loop_toggled(
        self,
        _sender: Sender,
        app_data: bool,
        user_data: str,
    ) -> None:
        self.call(
            self.on_loop_changed,
            user_data,
            app_data,
        )

    def _on_sample_double_clicked(
        self,
        _sender: Sender,
        app_data: List[int],
    ) -> None:
        clicked_item = app_data[1]
        user_data = dpg.get_item_user_data(clicked_item)
        if user_data is not None:
            _, voice_id = user_data
            self.call(self.on_sample_edit_requested, voice_id)

    def _on_sample_clicked(
        self,
        _sender: Sender,
        app_data: Tuple[int, int],
    ) -> None:
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        user_data = dpg.get_item_user_data(clicked_item)
        if user_data is None:
            return

        position, voice_id = user_data
        self._list_menu_pending = False
        self._show_context_menu(position, voice_id)

    def _on_list_right_clicked(
        self,
        _sender: Sender,
        _app_data: int,
    ) -> None:
        """Raises the list's own menu a frame later, leaving a row that answers the press first.

        Both doors are offered the same press, the list before the row, so the menu the list
        would raise waits a frame: a row landed on claims the press in the meantime and states
        the voice it holds, and an empty stretch of the list leaves the claim unmade.
        """
        if not self._pointer_within_list():
            return

        self._list_menu_pending = True
        FrameCallbackManager.set_frame_callback(self._show_list_menu)

    def _pointer_within_list(self) -> bool:
        """Whether the pointer stands over the voice list.

        The button above the list is laid out in the card that holds them both, so where the
        button was drawn places the list on screen as well.
        """
        return dpg_pointer_within_window(
            TAG_SEQUENCER_VOICES_WINDOW,
            TAG_SEQUENCER_VOICES_BUTTON_NEW_INSTRUMENT,
        )

    def _show_list_menu(self) -> None:
        """Prints the ways a voice comes in, for a press the list answered."""
        if not self._list_menu_pending:
            return

        self._list_menu_pending = False
        self._menu.show_pool()

    def _entry_for(self, voice_id: str) -> Optional[VoiceEntryViewModel]:
        return next((entry for entry in self._entries if entry.voice_id == voice_id), None)

    def _show_context_menu(self, position: int, voice_id: str) -> None:
        """Raises the menu of the row a press landed on, for the voice that row holds."""
        entry = self._entry_for(voice_id)
        if entry is None:
            return

        self._menu.show_for(
            VoiceSelection(
                voice_id=voice_id,
                position=position,
                name=entry.name,
                kind=entry.kind,
            )
        )

    @property
    def voice_count(self) -> int:
        """How many voices the list holds, which is what says where a move can carry one."""
        return len(self._entries)

    def owns_edit_actions(self) -> bool:
        """Whether the Edit menu states this panel's actions, which it does while it holds a sample.

        The menu offers what the next press would reach, so the key scope decides it, and the
        selection those keys act on is the one the actions are built for.
        """
        return self._keys_active() and self.selection is not None

    def build_edit_actions(self) -> None:
        """Builds the panel's whole action set for the voice the selection holds."""
        selection = self.selection
        if selection is not None:
            self._menu.add_action_items(selection)

    def build_voice_actions(self) -> None:
        """States the actions of the voice the list holds, for a menu listing the pool above them.

        The Voice menu prints the ways a voice comes in first, so the chosen voice's actions are
        led by a rule of their own here, and nothing is stated while no voice is chosen. The row
        menu draws its own dividers around the same set.
        """
        selection = self.selection
        if selection is None:
            return

        dpg.add_separator()
        self._menu.add_action_items(selection)

    @staticmethod
    def _label(
        language_manager: LanguageManager,
        element: SequencerVoicesElements,
    ) -> str:
        return language_manager[
            Page.SEQUENCER,
            Panel.VOICES,
            TextType.LABEL,
            element,
        ]

    @staticmethod
    def _tooltip(
        language_manager: LanguageManager,
        element: SequencerVoicesElements,
    ) -> str:
        return language_manager[
            Page.SEQUENCER,
            Panel.VOICES,
            TextType.TOOLTIP,
            element,
        ]
