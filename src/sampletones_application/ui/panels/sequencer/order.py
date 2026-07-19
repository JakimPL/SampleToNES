from typing import Callable, Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerOrderElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_ORDER_BUTTON_ADD,
    TAG_SEQUENCER_ORDER_BUTTON_REMOVE,
    TAG_SEQUENCER_ORDER_PANEL,
    TAG_SEQUENCER_ORDER_TABLE,
    TAG_SEQUENCER_ORDER_WINDOW,
    TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD,
    TAG_SEQUENCER_THEME_TABLE_ORDER,
)
from sampletones_application.ui.elements.context_menu import (
    add_play_menu_item,
    context_menu,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.table.caret import CaretOverlay
from sampletones_application.ui.elements.table.cells import EditableCells, pending_label
from sampletones_application.ui.panels.sequencer.columns import channel_color
from sampletones_application.ui.panels.sequencer.order_input import (
    INDEX_DIGITS,
    ORDER_ROWS,
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.themes.inline import create_selectable_text_theme
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_delete_item
from sampletones_application.utils.gui.keyboard import (
    PRIORITY_PANEL,
    KeyEvent,
    KeyRouter,
)
from sampletones_application.utils.gui.shortcuts.keys import HEX_KEYS, Modifier
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_application.view_model.sequencer.move import MoveDirection
from sampletones_application.view_model.sequencer.order import (
    SequencerOrderGridViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_id
from sampletones_shared.constants.symbols import MINUS, PLUS
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.color import with_alpha_fraction

OrderKey = Tuple[Optional[GeneratorName], int]

OnFrameSelectedCallback = Callable[[int], None]
OnRemoveCallback = Callable[[int], None]
OnFrameActionCallback = Callable[[int], None]
OnMoveCallback = Callable[[int, int], None]
OnSetOrderEntryCallback = Callable[[GeneratorName, int, Optional[int]], None]
OnSetMasterEntryCallback = Callable[[int, Optional[int]], None]

MASTER_TABLE_ROW: Final[int] = 0
DIVIDER_TABLE_ROW: Final[int] = 1

FROZEN_LABEL_COLUMNS: Final[int] = 1

_EMPTY_LABEL = display_id(None)


class GUISequencerOrderPanel(GUIPanel):
    """Editable, transposed view of the arrangement: positions are columns, channels rows.

    A single edit cursor moves over the cells; its position is the active frame, so
    moving it horizontally drives the tracker grid (``on_frame_selected``). The
    master row (``None``) broadcasts a typed index to every channel and shows ``?``
    when they disagree — the horizontal analog of the tracker's sample column.
    """

    def __init__(
        self,
        *,
        layout: SequencerLayout,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        initial_collapsed: bool = False,
    ) -> None:
        self._layout = layout
        self._router = key_router
        self._position_count: int = 0
        self._order: EditableCells[OrderKey] = EditableCells()
        self._input_state: OrderInputState = OrderInputState()
        self._highlighted: Optional[OrderCursor] = None
        self._highlighted_column: Optional[int] = None
        self._current_position: Optional[int] = None
        self._playing_position: Optional[int] = None
        self._cell_handler_tag = f"{TAG_SEQUENCER_ORDER_TABLE}{SUF_HANDLER_REGISTRY}"
        self._entry_theme: int = 0
        self._table_theme = ThemeRegistry.get(TAG_SEQUENCER_THEME_TABLE_ORDER)

        self.on_frame_selected: Optional[OnFrameSelectedCallback] = None
        self.on_remove_requested: Optional[OnRemoveCallback] = None
        self.on_duplicate_requested: Optional[OnFrameActionCallback] = None
        self.on_insert_requested: Optional[OnFrameActionCallback] = None
        self.on_clear_requested: Optional[OnFrameActionCallback] = None
        self.on_play_from_requested: Optional[OnFrameActionCallback] = None
        self.on_move_requested: Optional[OnMoveCallback] = None
        self.on_set_order_entry: Optional[OnSetOrderEntryCallback] = None
        self.on_set_master_entry: Optional[OnSetMasterEntryCallback] = None
        self.on_cell_selected: Optional[VoidCallback] = None

        self._lbl_order = language_manager[
            Page.SEQUENCER,
            Panel.ORDER,
            TextType.LABEL,
            SequencerOrderElements.ORDER_TEXT,
        ]
        self._row_labels: Dict[Optional[GeneratorName], str] = {
            None: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.ROW_MASTER,
            ],
            GeneratorName.PULSE1: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.ROW_PULSE_1,
            ],
            GeneratorName.PULSE2: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.ROW_PULSE_2,
            ],
            GeneratorName.TRIANGLE: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.ROW_TRIANGLE,
            ],
            GeneratorName.NOISE: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.ROW_NOISE,
            ],
        }

        def _context_label(element: SequencerOrderElements) -> str:
            return language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                element,
            ]

        self._lbl_context_play = _context_label(SequencerOrderElements.CONTEXT_PLAY)
        self._lbl_context_duplicate = _context_label(SequencerOrderElements.CONTEXT_DUPLICATE)
        self._lbl_context_insert = _context_label(SequencerOrderElements.CONTEXT_INSERT)
        self._lbl_context_clear = _context_label(SequencerOrderElements.CONTEXT_CLEAR)
        self._lbl_context_remove = _context_label(SequencerOrderElements.CONTEXT_REMOVE)
        self._lbl_context_move_left = _context_label(SequencerOrderElements.CONTEXT_MOVE_LEFT)
        self._lbl_context_move_right = _context_label(SequencerOrderElements.CONTEXT_MOVE_RIGHT)
        self._lbl_context_move_start = _context_label(SequencerOrderElements.CONTEXT_MOVE_START)
        self._lbl_context_move_end = _context_label(SequencerOrderElements.CONTEXT_MOVE_END)

        self._sc_move_left = Shortcut(dpg.mvKey_Left, (Modifier.ALT,)).get_display_string()
        self._sc_move_right = Shortcut(dpg.mvKey_Right, (Modifier.ALT,)).get_display_string()
        self._sc_move_start = Shortcut(dpg.mvKey_Home, (Modifier.ALT,)).get_display_string()
        self._sc_move_end = Shortcut(dpg.mvKey_End, (Modifier.ALT,)).get_display_string()
        self._sc_duplicate = Shortcut(dpg.mvKey_D, (Modifier.CTRL,)).get_display_string()
        self._sc_insert = PLUS
        self._sc_remove = MINUS
        self._sc_clear = Shortcut(dpg.mvKey_Delete, (Modifier.SHIFT,)).get_display_string()

        super().__init__(
            tag=TAG_SEQUENCER_ORDER_PANEL,
        )
        self._enable_vertical_collapse(
            initial_collapsed=initial_collapsed,
            auto_height=True,
            card_tag=TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD,
        )

    def create_panel(self, parent: str) -> None:
        self._create_entry_themes()
        with self._collapsible_card(
            parent,
            self._lbl_order,
            glyph=self._glyphs.headers.order,
        ):
            with dpg.group(tag=self.tag):
                self._create_button_row()
                self._create_order_window()
                self._register_handlers()

    def _create_entry_themes(self) -> None:
        """Colours every pattern entry with one readable colour.

        The theme targets only the selectable text, so it leaves every other colour to
        the global theme rather than shadowing it.
        """
        self._entry_theme = create_selectable_text_theme(self._layout.colors.text.order)

    def _create_button_row(self) -> None:
        with dpg.group(horizontal=True, parent=self.tag):
            dpg.add_button(
                tag=TAG_SEQUENCER_ORDER_BUTTON_ADD,
                label=PLUS,
                callback=self._on_add_clicked,
            )
            dpg.add_button(
                tag=TAG_SEQUENCER_ORDER_BUTTON_REMOVE,
                label=MINUS,
                callback=self._on_remove_clicked,
                enabled=False,
            )

    def _create_order_window(self) -> None:
        dpg.add_child_window(
            tag=TAG_SEQUENCER_ORDER_WINDOW,
            parent=self.tag,
            height=self._layout.order.height,
            width=0,
            border=False,
        )

    def _register_handlers(self) -> None:
        self._router.register(
            self._on_key_pressed,
            priority=PRIORITY_PANEL,
            active=self._keys_active,
        )

        with dpg.item_handler_registry(tag=self._cell_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_cell_right_clicked)

    def update_order(self, view_model: SequencerOrderGridViewModel) -> None:
        """Reconciles the order table; rebuilds only when the position count changes."""
        cell_values = self._compute_cell_values(view_model)
        if view_model.position_count != self._position_count:
            self._rebuild_table(view_model, cell_values)
        else:
            self._order.reconcile(cell_values, self._render_cell)

        dpg_configure_item(
            TAG_SEQUENCER_ORDER_BUTTON_REMOVE,
            enabled=view_model.position_count > 0,
        )

    def select_position(self, frame: int) -> None:
        """Follows the tracker frame: always updates the unfocused column highlight;
        also moves the edit cursor when one is active.
        """
        self._current_position = frame
        cursor = self._input_state.cursor
        if cursor is not None:
            if cursor.position == frame:
                return

            new_state = OrderInputState(cursor=OrderCursor(cursor.generator, frame))
            if 0 <= frame < self._position_count:
                self._apply_state(new_state, notify=False)
            else:
                self._clear_cursor_highlight()
                self._clear_column_highlight()
                self._input_state = new_state
                self._update_caret()
        else:
            if self._highlighted_column == frame:
                return

            self._clear_column_highlight()
            if 0 <= frame < self._position_count:
                self._apply_column_highlight(frame, focused=False)

    def deselect_cell(self) -> None:
        """Drops the edit cursor (e.g. when focus moves to the tracker grid)."""
        cursor = self._input_state.cursor
        self._clear_cursor_highlight()
        self._clear_column_highlight()
        self._input_state = OrderInputState()
        self._update_caret()

        if cursor is not None:
            self._update_cell_display(cursor)

        if self._current_position is not None and 0 <= self._current_position < self._position_count:
            self._apply_column_highlight(self._current_position, focused=False)

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_ORDER_PANEL, enabled=enabled)

    def _compute_cell_values(
        self,
        view_model: SequencerOrderGridViewModel,
    ) -> Dict[OrderKey, str]:
        cell_values: Dict[OrderKey, str] = {}
        for position in range(view_model.position_count):
            cell_values[(None, position)] = view_model.master_label(position)
            for generator in GeneratorName.items():
                cell_values[(generator, position)] = view_model.entry_label(
                    generator,
                    position,
                )

        return cell_values

    def _rebuild_table(
        self,
        view_model: SequencerOrderGridViewModel,
        cell_values: Dict[OrderKey, str],
    ) -> None:
        """Recreates the whole table when the position count changes.

        Deleting and re-adding a live table's *columns* leaves DPG's per-column
        state (and any highlight keyed by column index) dangling, which corrupted
        the heap. Replacing the table item wholesale sidesteps that: the cursor and
        column highlights die with the old table, so nothing references freed
        columns.
        """
        dpg_delete_item(TAG_SEQUENCER_ORDER_TABLE)
        self._highlighted = None
        self._highlighted_column = None
        self._order.reset(cell_values)
        self._position_count = view_model.position_count
        self._build_table(view_model.position_count)
        self._restore_cursor()

    def _build_table(self, position_count: int) -> None:
        dpg.add_table(
            tag=TAG_SEQUENCER_ORDER_TABLE,
            parent=TAG_SEQUENCER_ORDER_WINDOW,
            header_row=True,
            resizable=False,
            borders_innerH=True,
            borders_innerV=True,
            borders_outerH=True,
            borders_outerV=True,
            scrollX=True,
            scrollY=False,
            freeze_columns=FROZEN_LABEL_COLUMNS,
            policy=dpg.mvTable_SizingFixedFit,
        )
        FontRegistry.bind_to_item(TAG_SEQUENCER_ORDER_TABLE, Font.MONO_BOLD)
        self._table_theme.bind_to_item(TAG_SEQUENCER_ORDER_TABLE)

        dpg.add_table_column(
            label="",
            parent=TAG_SEQUENCER_ORDER_TABLE,
            width_fixed=True,
            init_width_or_weight=self._layout.table_cells.generator,
        )
        for position in range(position_count):
            dpg.add_table_column(
                label=display_id(position),
                parent=TAG_SEQUENCER_ORDER_TABLE,
                width_fixed=True,
                init_width_or_weight=self._layout.order.position_column_width,
            )

        for generator in ORDER_ROWS:
            self._build_row(generator, position_count)
            if generator is None:
                self._build_divider_row(position_count)

        self._apply_column_backgrounds()
        self._highlight_master_row(position_count)
        self._tint_channel_rows()

    def _apply_column_backgrounds(self) -> None:
        """Tints the label column like the header row.

        The position columns carry no static shade, so the per-channel row tints read
        cleanly beneath the position and cursor highlights — the transposed analog of
        the tracker grid, whose channel column tints sit beneath its cursor.
        """
        dpg.highlight_table_column(
            TAG_SEQUENCER_ORDER_TABLE,
            0,
            self._layout.colors.order.label,
        )

    def _highlight_master_row(self, position_count: int) -> None:
        """Tints the master row and the rule below it, matching the tracker grid's
        sample column and sample divider so the two tables read consistently.

        The tint is applied per cell so it overrides the per-column shades and reads
        consistently across the whole row.
        """
        for column in range(position_count + 1):
            self._highlight_master_cell_at(column)
            dpg.highlight_table_cell(
                TAG_SEQUENCER_ORDER_TABLE,
                DIVIDER_TABLE_ROW,
                column,
                color=self._layout.colors.order.master_divider,
            )

    def _highlight_master_cell_at(self, column: int) -> None:
        dpg.highlight_table_cell(
            TAG_SEQUENCER_ORDER_TABLE,
            MASTER_TABLE_ROW,
            column,
            color=self._layout.colors.order.master,
        )

    def _tint_channel_rows(self) -> None:
        """Washes each channel row with a light tint of its identity colour.

        Uses a row highlight, not per-cell tints, so it sits on a layer beneath the
        position and cursor highlights — those keep working and a cleared cursor cell
        falls back to the row tint instead of a bare patch. This is the transposed
        analog of the tracker grid's per-channel column tint, sharing the fraction.
        """
        channels = self._layout.colors.channels
        fraction = self._layout.tracker.channel_column_tint
        for generator in GeneratorName.items():
            tint = with_alpha_fraction(
                channel_color(channels, generator),
                fraction,
            )
            dpg.highlight_table_row(
                TAG_SEQUENCER_ORDER_TABLE,
                self._table_row(generator),
                tint,
            )

    def _apply_column_highlight(self, position: int, *, focused: bool) -> None:
        if focused:
            color = self._layout.colors.pattern_highlight
        elif position == self._playing_position:
            color = self._layout.colors.order.column_playing
        else:
            color = self._layout.colors.order.column_current

        dpg.highlight_table_column(TAG_SEQUENCER_ORDER_TABLE, position + 1, color)
        self._highlighted_column = position

    def set_playing_position(self, position: Optional[int]) -> None:
        previous_position = self._playing_position
        self._playing_position = position
        if (
            previous_position is not None
            and previous_position != position
            and previous_position == self._highlighted_column
        ):
            focused = self._input_state.cursor is not None and self._input_state.cursor.position == previous_position
            self._apply_column_highlight(previous_position, focused=focused)

    def _clear_column_highlight(self) -> None:
        if self._highlighted_column is not None:
            dpg.unhighlight_table_column(
                TAG_SEQUENCER_ORDER_TABLE,
                self._highlighted_column + 1,
            )
            self._highlighted_column = None

    def _build_row(
        self,
        generator: Optional[GeneratorName],
        position_count: int,
    ) -> None:
        font = Font.MONO_BOLD_SMALL if generator is None else Font.MONO_SMALL
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_ORDER_TABLE)

        label_cell = dpg.add_table_cell(parent=row_id)
        label_text = dpg.add_text(
            self._row_labels[generator],
            parent=label_cell,
            color=self._layout.colors.label,
        )
        FontRegistry.bind_to_item(label_text, Font.MONO_BOLD_SMALL)

        for position in range(position_count):
            cell = dpg.add_table_cell(parent=row_id)
            key: OrderKey = (generator, position)
            selectable = dpg.add_selectable(
                parent=cell,
                label=self._render_cell(key),
                user_data=key,
                callback=self._on_cell_clicked,
            )
            FontRegistry.bind_to_item(selectable, font)
            dpg.bind_item_theme(selectable, self._entry_theme)
            dpg.bind_item_handler_registry(selectable, self._cell_handler_tag)
            self._order.register(key, selectable)

    def _build_divider_row(self, position_count: int) -> None:
        """Inserts the thin rule that sets the master row apart from the channel
        rows — the transposed analog of the tracker grid's sample-divider column.
        """
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_ORDER_TABLE)
        spacer_cell = dpg.add_table_cell(parent=row_id)
        dpg.add_spacer(
            parent=spacer_cell,
            height=self._layout.order.master_divider_height,
        )
        for _ in range(position_count):
            dpg.add_table_cell(parent=row_id)

    def _render_cell(self, key: OrderKey) -> str:
        cursor = self._input_state.cursor
        stored = self._order.values.get(key, _EMPTY_LABEL)
        if cursor is not None and (cursor.generator, cursor.position) == key:
            return pending_label(
                self._input_state.pending,
                stored,
                INDEX_DIGITS,
            )

        return stored

    def _table_row(self, generator: Optional[GeneratorName]) -> int:
        if generator is None:
            return MASTER_TABLE_ROW
        return ORDER_ROWS.index(generator) + 1

    def _apply_cursor_highlight(self, cursor: OrderCursor) -> None:
        dpg.highlight_table_cell(
            TAG_SEQUENCER_ORDER_TABLE,
            self._table_row(cursor.generator),
            cursor.position + 1,
            color=self._layout.colors.cell_cursor,
        )
        self._highlighted = cursor

    def _clear_cursor_highlight(self) -> None:
        if self._highlighted is None:
            return

        cursor = self._highlighted
        self._highlighted = None
        if cursor.generator is None:
            self._highlight_master_cell_at(cursor.position + 1)
        else:
            dpg.unhighlight_table_cell(
                TAG_SEQUENCER_ORDER_TABLE,
                self._table_row(cursor.generator),
                cursor.position + 1,
            )

    def _restore_cursor(self) -> None:
        cursor = self._input_state.cursor
        if cursor is None or self._position_count == 0:
            self._input_state = OrderInputState()
            if self._current_position is not None and 0 <= self._current_position < self._position_count:
                self._apply_column_highlight(
                    self._current_position,
                    focused=False,
                )

            self._update_caret()
            return

        position = min(cursor.position, self._position_count - 1)
        clamped = OrderCursor(cursor.generator, position)
        self._input_state = OrderInputState(cursor=clamped)
        self._apply_cursor_highlight(clamped)
        self._apply_column_highlight(clamped.position, focused=True)
        self._update_caret()

    def _apply_state(
        self,
        new_state: OrderInputState,
        notify: bool = True,
    ) -> None:
        old = self._input_state.cursor
        new = new_state.cursor

        self._clear_cursor_highlight()
        self._input_state = new_state

        if old is not None:
            self._update_cell_display(old)

        if new is not None:
            self._apply_cursor_highlight(new)
            self._update_cell_display(new)

        old_position = old.position if old is not None else None
        new_position = new.position if new is not None else None
        if old_position != new_position:
            self._clear_column_highlight()
            if new_position is not None:
                self._current_position = new_position
                self._apply_column_highlight(new_position, focused=True)

        if notify and new is not None:
            self.call(self.on_cell_selected)
            if old is None or old.position != new.position:
                self.call(self.on_frame_selected, new.position)

        self._update_caret()

    def _update_cell_display(self, cursor: OrderCursor) -> None:
        key: OrderKey = (cursor.generator, cursor.position)
        widget = self._order.widget(key)
        if widget is not None:
            dpg.configure_item(widget, label=self._render_cell(key))

    def _update_caret(self) -> None:
        """Arms (or clears) the shared caret box on the active order cell."""
        cursor = self._input_state.cursor
        if cursor is None:
            CaretOverlay.clear(TAG_SEQUENCER_ORDER_TABLE)
            return

        key: OrderKey = (cursor.generator, cursor.position)
        font = Font.MONO_BOLD_SMALL if cursor.generator is None else Font.MONO_SMALL
        CaretOverlay.set_target(
            owner=TAG_SEQUENCER_ORDER_TABLE,
            widget=self._order.widget(key),
            caret_index=len(self._input_state.pending),
            font=font,
            clip_widget=TAG_SEQUENCER_ORDER_WINDOW,
        )

    def _on_cell_clicked(
        self,
        sender: Sender,
        app_data: bool,
        user_data: OrderKey,
    ) -> None:
        dpg.set_value(sender, False)
        self._committed_state()
        generator, position = user_data
        self._apply_state(OrderInputState(cursor=OrderCursor(generator, position)))

    def _on_cell_right_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
    ) -> None:
        """Opens the frame-operations menu for the right-clicked frame.

        The menu acts on the clicked frame directly and leaves the edit cursor (and, while
        following playback, the playhead) where it is — right-clicking should not seek.
        """
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        key = dpg.get_item_user_data(clicked_item)
        if key is None:
            return

        _, position = key
        self._show_context_menu(position)

    def _show_context_menu(self, position: int) -> None:
        with context_menu():
            header = dpg.add_text(display_id(position))
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            add_play_menu_item(
                self._lbl_context_play,
                lambda: self.call(self.on_play_from_requested, position),
            )
            dpg.add_separator()
            dpg.add_menu_item(
                label=self._lbl_context_duplicate,
                shortcut=self._sc_duplicate,
                callback=lambda: self.call(self.on_duplicate_requested, position),
            )
            dpg.add_menu_item(
                label=self._lbl_context_insert,
                shortcut=self._sc_insert,
                callback=lambda: self.call(self.on_insert_requested, position),
            )
            dpg.add_menu_item(
                label=self._lbl_context_clear,
                shortcut=self._sc_clear,
                callback=lambda: self.call(self.on_clear_requested, position),
            )
            dpg.add_menu_item(
                label=self._lbl_context_remove,
                shortcut=self._sc_remove,
                callback=lambda: self.call(self.on_remove_requested, position),
            )
            dpg.add_separator()
            self._add_move_item(self._lbl_context_move_left, self._sc_move_left, position, MoveDirection.PREVIOUS)
            self._add_move_item(self._lbl_context_move_right, self._sc_move_right, position, MoveDirection.NEXT)
            self._add_move_item(self._lbl_context_move_start, self._sc_move_start, position, MoveDirection.FIRST)
            self._add_move_item(self._lbl_context_move_end, self._sc_move_end, position, MoveDirection.LAST)

    def _add_move_item(self, label: str, shortcut: str, position: int, direction: MoveDirection) -> None:
        """Adds a move item, greyed out (disabled) when the move would have no effect."""
        target = direction.target(position, self._position_count)
        dpg.add_menu_item(
            label=label,
            shortcut=shortcut,
            enabled=target is not None,
            callback=lambda: self.call(self.on_move_requested, position, target),
        )

    def _keys_active(self) -> bool:
        """Whether the order table owns the next key: its cursor is set and nothing else holds the keyboard.

        A focused field or an open modal keeps the keyboard, so the table stands down while the user
        types into an input or answers a dialog.
        """
        return (
            self._input_state.cursor is not None
            and not self._router.is_field_focused
            and not self._router.is_modal_open
        )

    def _on_key_pressed(self, event: KeyEvent) -> bool:
        """Applies an order key to the active cell, reporting whether the table consumed it.

        Alt drives the frame moves and Ctrl+D duplicates; any other modifier press belongs to the
        application's global shortcuts, so the table yields it and keeps the plain keys for editing.
        """
        cursor = self._input_state.cursor
        if cursor is None:
            return False

        if event.alt:
            return self._handle_alt_move(event.key, cursor.position)

        if event.ctrl:
            if event.key == dpg.mvKey_D:
                self.call(self.on_duplicate_requested, cursor.position)
                return True
            return False

        match event.key:
            case dpg.mvKey_Plus | dpg.mvKey_Add:
                self.call(self.on_insert_requested, cursor.position)
            case dpg.mvKey_Minus | dpg.mvKey_Subtract:
                self._on_remove_clicked()
            case dpg.mvKey_Left:
                self._move_position(-1)
            case dpg.mvKey_Right:
                self._move_position(1)
            case dpg.mvKey_Up:
                self._move_channel(-1)
            case dpg.mvKey_Down:
                self._move_channel(1)
            case dpg.mvKey_Home:
                self._jump_position(0)
            case dpg.mvKey_End:
                self._jump_position(self._position_count - 1)
            case dpg.mvKey_Return:
                self._move_position(1)
            case dpg.mvKey_Delete:
                if event.shift:
                    self.call(self.on_clear_requested, cursor.position)
                else:
                    self._clear_cell()
                    self._move_position(1)
            case dpg.mvKey_Back:
                self._clear_cell()
                self._move_position(-1)
            case dpg.mvKey_Insert:
                self._on_add_clicked()
            case dpg.mvKey_Escape:
                self._apply_state(self._input_state.cancel())
            case _:
                return self._handle_printable_key(event.key)

        return True

    def _handle_alt_move(self, key: int, position: int) -> bool:
        """Moves the selected frame left/right/to-start/to-end on Alt + arrow / Home / End.

        Returns whether the key was an Alt move gesture, so a boundary with nowhere to go still
        counts as consumed and stays out of the global shortcuts.
        """
        direction = self._alt_move_direction(key)
        if direction is None:
            return False

        target = direction.target(position, self._position_count)
        if target is not None:
            self.call(self.on_move_requested, position, target)

        return True

    def _alt_move_direction(self, key: int) -> Optional[MoveDirection]:
        match key:
            case dpg.mvKey_Left:
                return MoveDirection.PREVIOUS
            case dpg.mvKey_Right:
                return MoveDirection.NEXT
            case dpg.mvKey_Home:
                return MoveDirection.FIRST
            case dpg.mvKey_End:
                return MoveDirection.LAST
            case _:
                return None

    def _move_position(self, delta: int) -> None:
        self._apply_state(
            self._committed_state().navigate_position(delta, self._position_count),
        )

    def _jump_position(self, index: int) -> None:
        self._apply_state(
            self._committed_state().navigate_position(
                index,
                self._position_count,
                absolute=True,
            ),
        )

    def _move_channel(self, delta: int) -> None:
        self._apply_state(self._committed_state().navigate_channel(delta))

    def _committed_state(self) -> OrderInputState:
        state, index = self._input_state.commit_partial()
        if index is not None:
            self._emit(self._input_state.cursor, index)

        return state

    def _handle_printable_key(self, key: int) -> bool:
        char = HEX_KEYS.get(key)
        if char is None:
            return False

        new_state, index = self._input_state.type_char(char)
        if index is not None:
            self._emit(self._input_state.cursor, index)
            new_state = new_state.navigate_position(1, self._position_count)

        self._apply_state(new_state)
        return True

    def _clear_cell(self) -> None:
        """Empties the cell under the cursor (sets its slot to ``None``).

        Mirrors the tracker's clear: a channel cell empties just that channel's
        slot; the master row empties every channel at that position.
        """
        cursor = self._input_state.cursor
        if cursor is None:
            return

        self._emit(cursor, None)
        self._apply_state(self._input_state.cancel())

    def _emit(
        self,
        cursor: Optional[OrderCursor],
        index: Optional[int],
    ) -> None:
        if cursor is None:
            return

        if cursor.generator is None:
            self.call(self.on_set_master_entry, cursor.position, index)
        else:
            self.call(
                self.on_set_order_entry,
                cursor.generator,
                cursor.position,
                index,
            )

    def _get_cursor_position(self) -> Optional[int]:
        cursor = self._input_state.cursor
        return cursor.position if cursor is not None else self._current_position

    def _on_add_clicked(self) -> None:
        """Inserts an empty frame after the current one (appends when at or past the end)."""
        position = self._get_cursor_position()
        if position is None or not 0 <= position < self._position_count:
            position = self._position_count - 1

        self.call(self.on_insert_requested, position)

    def _on_remove_clicked(self) -> None:
        position = self._get_cursor_position()
        if position is not None and 0 <= position < self._position_count:
            self.call(self.on_remove_requested, position)
