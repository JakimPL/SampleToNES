from typing import Callable, Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.elements.sequencer import (
    SequencerInstrumentsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_INSTRUMENTS_HANDLER_KEY,
    TAG_SEQUENCER_INSTRUMENTS_INPUT_RENAME,
    TAG_SEQUENCER_INSTRUMENTS_PANEL,
    TAG_SEQUENCER_INSTRUMENTS_TABLE,
    TAG_SEQUENCER_INSTRUMENTS_THEME_ROW,
    TAG_SEQUENCER_INSTRUMENTS_WINDOW,
)
from sampletones_application.ui.elements.context_menu import (
    add_play_menu_item,
    context_menu,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_delete_children
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.view_model.sequencer.move import MoveDirection
from sampletones_application.view_model.sequencer.samples import (
    SampleEntryViewModel,
    SequencerSamplesViewModel,
)
from sampletones_core.utils.display import display_id, display_sample_label
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import StringCallback

FROZEN_HEADER_ROWS: Final[int] = 1


class GUISequencerSamplesPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: SequencerLayout,
        language_manager: LanguageManager,
        shortcut_manager: ShortcutManager,
        initial_collapsed: bool = False,
    ) -> None:
        self._layout = layout
        self._shortcut_manager = shortcut_manager
        self._row_handler_tag = f"{TAG_SEQUENCER_INSTRUMENTS_TABLE}{SUF_HANDLER_REGISTRY}"
        self._rename_handler_tag = f"{TAG_SEQUENCER_INSTRUMENTS_INPUT_RENAME}{SUF_HANDLER_REGISTRY}"
        self._selected_sample_id: Optional[str] = None
        self._selected_row: Optional[int] = None
        self._editing_sample_id: Optional[str] = None
        self._entries: Tuple[SampleEntryViewModel, ...] = ()
        self.on_sample_selected: Optional[StringCallback] = None
        self.on_sample_edit_requested: Optional[StringCallback] = None
        self.on_loop_changed: Optional[Callable[[str, bool], None]] = None
        self.on_remove_requested: Optional[StringCallback] = None
        self.on_play_requested: Optional[StringCallback] = None
        self.on_move_requested: Optional[Callable[[str, int], None]] = None
        self.on_rename_committed: Optional[Callable[[str, str], None]] = None
        self.on_duplicate_requested: Optional[StringCallback] = None
        self._lbl_instruments = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.INSTRUMENTS_TEXT,
        ]
        self._lbl_column_id = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.COLUMN_ID,
        ]
        self._lbl_column_name = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.COLUMN_NAME,
        ]
        self._lbl_column_loop = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.COLUMN_LOOP,
        ]
        self._lbl_context_play = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.PLAY,
        ]
        self._lbl_context_edit = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.CONTEXT_EDIT,
        ]
        self._lbl_context_rename = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.CONTEXT_RENAME,
        ]
        self._lbl_context_duplicate = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.CONTEXT_DUPLICATE,
        ]
        self._lbl_context_remove = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.CONTEXT_REMOVE,
        ]
        self._lbl_context_move_up = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.CONTEXT_MOVE_UP,
        ]
        self._lbl_context_move_down = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.CONTEXT_MOVE_DOWN,
        ]
        self._lbl_context_move_top = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.CONTEXT_MOVE_TOP,
        ]
        self._lbl_context_move_bottom = language_manager[
            Page.SEQUENCER,
            Panel.INSTRUMENTS,
            TextType.LABEL,
            SequencerInstrumentsElements.CONTEXT_MOVE_BOTTOM,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_INSTRUMENTS_PANEL,
            width=-1,
            height=-layout.history.height,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._lbl_instruments,
            glyph=self._glyphs.headers.samples,
        ):
            self._create_samples_table()

        self._create_row_handlers()
        self._create_rename_handler()
        self._create_key_handler()

    def _create_row_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._row_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_sample_clicked)
            dpg.add_item_double_clicked_handler(callback=self._on_sample_double_clicked)

    def _create_rename_handler(self) -> None:
        with dpg.item_handler_registry(tag=self._rename_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_rename_deactivated)

        self._shortcut_manager.attach_focus_tracking(self._rename_handler_tag)

    def _create_key_handler(self) -> None:
        with dpg.handler_registry(tag=TAG_SEQUENCER_INSTRUMENTS_HANDLER_KEY):
            dpg.add_key_press_handler(callback=self._on_key_pressed)

    def _create_samples_table(self) -> None:
        with dpg.child_window(
            tag=TAG_SEQUENCER_INSTRUMENTS_WINDOW,
            border=False,
            width=-1,
            height=-1,
        ):
            with dpg.table(
                tag=TAG_SEQUENCER_INSTRUMENTS_TABLE,
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
            ):
                dpg.add_table_column(
                    label=self._lbl_column_id,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.instrument.id,
                )
                dpg.add_table_column(
                    label=self._lbl_column_name,
                    width_stretch=True,
                    init_width_or_weight=self._layout.table_cells.instrument.name,
                )
                dpg.add_table_column(
                    label=self._lbl_column_loop,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.instrument.loop,
                )
        ThemeRegistry.get(TAG_SEQUENCER_INSTRUMENTS_THEME_ROW).bind_to_item(TAG_SEQUENCER_INSTRUMENTS_TABLE)

    def update_view(self, view_model: SequencerSamplesViewModel) -> None:
        self._entries = view_model.samples
        self._editing_sample_id = None
        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuilds the samples table from the cached entries with explicit parents.

        Items pass an explicit ``parent`` so each widget binds directly: the browser
        tree builds on a worker thread and the DearPyGui container stack is
        process-global, so explicit parents keep this build independent of that
        shared stack.
        """
        dpg_delete_children(TAG_SEQUENCER_INSTRUMENTS_TABLE, slot=1)
        self._selected_row = None
        for position, entry in enumerate(self._entries):
            self._build_sample_row(position, entry)
        if self._selected_row is None:
            self._selected_sample_id = None

    def _build_sample_row(self, position: int, entry: SampleEntryViewModel) -> None:
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_INSTRUMENTS_TABLE)
        self._build_id_cell(row_id, position, entry)
        self._build_name_cell(row_id, position, entry)
        self._build_loop_cell(row_id, entry)
        if entry.sample_id == self._selected_sample_id:
            self._selected_row = position
            dpg.highlight_table_row(TAG_SEQUENCER_INSTRUMENTS_TABLE, position, color=self._layout.colors.cell_cursor)

    def _build_id_cell(self, row_id: int | str, position: int, entry: SampleEntryViewModel) -> None:
        id_cell = dpg.add_table_cell(parent=row_id)
        id_selectable = dpg.add_selectable(
            parent=id_cell,
            label=display_id(position),
            user_data=(position, entry.sample_id),
            callback=self._on_sample_selected,
        )
        FontRegistry.bind_to_item(id_selectable, Font.MONO_SMALL)
        dpg.bind_item_handler_registry(id_selectable, self._row_handler_tag)

    def _build_name_cell(self, row_id: int | str, position: int, entry: SampleEntryViewModel) -> None:
        name_cell = dpg.add_table_cell(parent=row_id)
        if entry.sample_id == self._editing_sample_id:
            self._build_name_input(name_cell, entry)
        else:
            self._build_name_selectable(name_cell, position, entry)

    def _build_name_selectable(self, name_cell: int | str, position: int, entry: SampleEntryViewModel) -> None:
        name_selectable = dpg.add_selectable(
            parent=name_cell,
            label=entry.name,
            user_data=(position, entry.sample_id),
            callback=self._on_sample_selected,
        )
        FontRegistry.bind_to_item(name_selectable, Font.MONO_SMALL)
        dpg.bind_item_handler_registry(name_selectable, self._row_handler_tag)

    def _build_name_input(self, name_cell: int | str, entry: SampleEntryViewModel) -> None:
        name_input = dpg.add_input_text(
            tag=TAG_SEQUENCER_INSTRUMENTS_INPUT_RENAME,
            parent=name_cell,
            default_value=entry.name,
            width=-1,
            on_enter=True,
            callback=self._on_rename_enter,
        )
        FontRegistry.bind_to_item(name_input, Font.MONO_SMALL)
        dpg.bind_item_handler_registry(name_input, self._rename_handler_tag)

    def _build_loop_cell(self, row_id: int | str, entry: SampleEntryViewModel) -> None:
        loop_cell = dpg.add_table_cell(parent=row_id)
        loop_checkbox = dpg.add_checkbox(
            parent=loop_cell,
            default_value=entry.loop,
            user_data=entry.sample_id,
            callback=self._on_loop_toggled,
        )
        FontRegistry.bind_to_item(loop_checkbox, Font.REGULAR_SMALL)

    def _on_sample_selected(self, sender: Sender, app_data: bool, user_data: Tuple[int, str]) -> None:
        position, sample_id = user_data
        dpg.set_value(sender, False)
        if self._selected_row is not None:
            dpg.unhighlight_table_row(TAG_SEQUENCER_INSTRUMENTS_TABLE, self._selected_row)

        self._selected_row = position
        self._selected_sample_id = sample_id
        dpg.highlight_table_row(TAG_SEQUENCER_INSTRUMENTS_TABLE, position, color=self._layout.colors.cell_cursor)
        self.call(self.on_sample_selected, sample_id)

    def deselect(self) -> None:
        """Drops the sample selection so the panel stops consuming keystrokes.

        Mirrors the grid and order panels: the three share global key handlers, so
        only the panel holding a selection acts on a keystroke. Selecting a cell in
        another panel clears this one's selection via this method.
        """
        if self._selected_row is not None:
            dpg.unhighlight_table_row(
                TAG_SEQUENCER_INSTRUMENTS_TABLE,
                self._selected_row,
            )

        self._selected_row = None
        self._selected_sample_id = None

    def _on_key_pressed(self, sender: Sender, app_data: int) -> None:
        if self._editing_sample_id is not None:
            if app_data == dpg.mvKey_Escape:
                self._cancel_rename()
            return

        if self._shortcut_manager.is_input_focused:
            return

        if self._selected_sample_id is None:
            return

        if self._alt_held():
            self._handle_alt_move(app_data)
            return

        if app_data == dpg.mvKey_Delete:
            self.call(self.on_remove_requested, self._selected_sample_id)
        elif app_data == dpg.mvKey_F2:
            self._start_rename(self._selected_sample_id)

    def _alt_held(self) -> bool:
        return bool(dpg.is_key_down(dpg.mvKey_LAlt) or dpg.is_key_down(dpg.mvKey_RAlt))

    def _handle_alt_move(self, key: int) -> None:
        """Moves the selected sample up/down/to-top/to-bottom on Alt + arrow / Home / End."""
        direction = self._alt_move_direction(key)
        if direction is None or self._selected_sample_id is None or self._selected_row is None:
            return

        target = direction.target(self._selected_row, len(self._entries))
        if target is not None:
            self.call(self.on_move_requested, self._selected_sample_id, target)

    def _alt_move_direction(self, key: int) -> Optional[MoveDirection]:
        match key:
            case dpg.mvKey_Up:
                return MoveDirection.PREVIOUS
            case dpg.mvKey_Down:
                return MoveDirection.NEXT
            case dpg.mvKey_Home:
                return MoveDirection.FIRST
            case dpg.mvKey_End:
                return MoveDirection.LAST
            case _:
                return None

    def _start_rename(self, sample_id: str) -> None:
        """Turns the sample's name cell into a focused text input."""
        if self._entry_for(sample_id) is None:
            return

        self._editing_sample_id = sample_id
        self._rebuild()
        FrameCallbackManager.set_frame_callback(lambda: dpg.focus_item(TAG_SEQUENCER_INSTRUMENTS_INPUT_RENAME))

    def _commit_rename(self) -> None:
        """Applies the edited name and restores the read-only cell.

        Clears the edit before notifying so the input's deactivated handler, fired
        during the teardown rebuild, sees the edit already finished.
        """
        if self._editing_sample_id is None:
            return

        sample_id = self._editing_sample_id
        name = dpg.get_value(TAG_SEQUENCER_INSTRUMENTS_INPUT_RENAME)
        self._editing_sample_id = None
        self.call(self.on_rename_committed, sample_id, name)
        self._rebuild()

    def _cancel_rename(self) -> None:
        if self._editing_sample_id is None:
            return

        self._editing_sample_id = None
        self._rebuild()

    def _on_rename_enter(self, sender: Sender, app_data: str) -> None:
        self._commit_rename()

    def _on_rename_deactivated(self, sender: Sender, app_data: int) -> None:
        self._commit_rename()

    def _on_loop_toggled(self, sender: Sender, app_data: bool, user_data: str) -> None:
        self.call(self.on_loop_changed, user_data, app_data)

    def _on_sample_double_clicked(self, sender: Sender, app_data: List[int]) -> None:
        clicked_item = app_data[1]
        user_data = dpg.get_item_user_data(clicked_item)
        if user_data is not None:
            _, sample_id = user_data
            self.call(self.on_sample_edit_requested, sample_id)

    def _on_sample_clicked(self, sender: Sender, app_data: Tuple[int, int]) -> None:
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        user_data = dpg.get_item_user_data(clicked_item)
        if user_data is None:
            return

        position, sample_id = user_data
        self._show_context_menu(position, sample_id)

    def _entry_for(self, sample_id: str) -> Optional[SampleEntryViewModel]:
        return next((entry for entry in self._entries if entry.sample_id == sample_id), None)

    def _show_context_menu(self, position: int, sample_id: str) -> None:
        entry = self._entry_for(sample_id)
        if entry is None:
            return

        with context_menu():
            header = dpg.add_text(display_sample_label(position, entry.name))
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            add_play_menu_item(self._lbl_context_play, lambda: self.call(self.on_play_requested, sample_id))
            dpg.add_menu_item(
                label=self._lbl_context_edit,
                callback=lambda: self.call(self.on_sample_edit_requested, sample_id),
            )
            dpg.add_menu_item(
                label=self._lbl_context_rename,
                callback=lambda: self._start_rename(sample_id),
            )
            dpg.add_menu_item(
                label=self._lbl_context_duplicate,
                callback=lambda: self.call(self.on_duplicate_requested, sample_id),
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label=self._lbl_context_remove,
                callback=lambda: self.call(self.on_remove_requested, sample_id),
            )
            dpg.add_separator()
            count = len(self._entries)
            self._add_move_item(self._lbl_context_move_up, sample_id, position, count, MoveDirection.PREVIOUS)
            self._add_move_item(self._lbl_context_move_down, sample_id, position, count, MoveDirection.NEXT)
            self._add_move_item(self._lbl_context_move_top, sample_id, position, count, MoveDirection.FIRST)
            self._add_move_item(self._lbl_context_move_bottom, sample_id, position, count, MoveDirection.LAST)

    def _add_move_item(
        self,
        label: str,
        sample_id: str,
        position: int,
        count: int,
        direction: MoveDirection,
    ) -> None:
        """Add a move item, greyed out (disabled) when the move would have no effect."""
        target = direction.target(position, count)
        dpg.add_menu_item(
            label=label,
            enabled=target is not None,
            callback=lambda: self.call(self.on_move_requested, sample_id, target),
        )
