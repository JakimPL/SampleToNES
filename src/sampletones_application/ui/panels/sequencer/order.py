from typing import Callable, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerOrderElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_ORDER_BUTTON_ADD,
    TAG_SEQUENCER_ORDER_BUTTON_REMOVE,
    TAG_SEQUENCER_ORDER_KEY_HANDLER,
    TAG_SEQUENCER_ORDER_PANEL,
    TAG_SEQUENCER_ORDER_TABLE,
    TAG_SEQUENCER_ORDER_WINDOW,
)
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.table.cells import EditableCells, active_label
from sampletones_application.ui.panels.sequencer.order_input import (
    INDEX_DIGITS,
    ORDER_ROWS,
    OrderCursor,
    OrderInputState,
)
from sampletones_application.utils.dpg import dpg_configure_item, dpg_delete_children
from sampletones_application.utils.shortcuts.keys import HEX_KEYS
from sampletones_application.view_model.sequencer.order import (
    SequencerOrderGridViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_id, display_index
from sampletones_shared.types.application import Sender

OrderKey = Tuple[Optional[GeneratorName], int]

OnFrameSelectedCallback = Callable[[int], None]
OnAddCallback = Callable[[], None]
OnRemoveCallback = Callable[[int], None]
OnSetOrderEntryCallback = Callable[[GeneratorName, int, int], None]
OnSetMasterEntryCallback = Callable[[int, int], None]

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
    ) -> None:
        self._layout = layout
        self._position_count: int = 0
        self._order: EditableCells[OrderKey] = EditableCells()
        self._input_state: OrderInputState = OrderInputState()

        self.on_frame_selected: Optional[OnFrameSelectedCallback] = None
        self.on_add_requested: Optional[OnAddCallback] = None
        self.on_remove_requested: Optional[OnRemoveCallback] = None
        self.on_set_order_entry: Optional[OnSetOrderEntryCallback] = None
        self.on_set_master_entry: Optional[OnSetMasterEntryCallback] = None

        self._lbl_order = language_manager[
            Page.SEQUENCER,
            Panel.ORDER,
            TextType.LABEL,
            SequencerOrderElements.ORDER_TEXT,
        ]
        self._row_labels: Dict[Optional[GeneratorName], str] = {
            None: language_manager[Page.SEQUENCER, Panel.ORDER, TextType.LABEL, SequencerOrderElements.COLUMN_MASTER],
            GeneratorName.PULSE1: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.COLUMN_PULSE_1,
            ],
            GeneratorName.PULSE2: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.COLUMN_PULSE_2,
            ],
            GeneratorName.TRIANGLE: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.COLUMN_TRIANGLE,
            ],
            GeneratorName.NOISE: language_manager[
                Page.SEQUENCER,
                Panel.ORDER,
                TextType.LABEL,
                SequencerOrderElements.COLUMN_NOISE,
            ],
        }

        super().__init__(
            tag=TAG_SEQUENCER_ORDER_PANEL,
            parent=TAG_SEQUENCER_GRID_PANEL,
        )

    def create_panel(self) -> None:
        with dpg.group(tag=self.tag, parent=self.parent):
            dpg.add_separator(parent=self.tag)
            header_text = dpg.add_text(self._lbl_order, parent=self.tag)
            FontRegistry.bind_to_item(header_text, Font.BOLD)
            self._create_button_row()
            self._create_order_window()
            self._register_key_handler()

    def _create_button_row(self) -> None:
        with dpg.group(horizontal=True, parent=self.tag):
            dpg.add_button(
                tag=TAG_SEQUENCER_ORDER_BUTTON_ADD,
                label="+",
                callback=self._on_add_clicked,
            )
            dpg.add_button(
                tag=TAG_SEQUENCER_ORDER_BUTTON_REMOVE,
                label="-",
                callback=self._on_remove_clicked,
                enabled=False,
            )

    def _create_order_window(self) -> None:
        with dpg.child_window(
            tag=TAG_SEQUENCER_ORDER_WINDOW,
            parent=self.tag,
            height=self._layout.order.height,
            width=0,
            border=False,
        ):
            with dpg.table(
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
                policy=dpg.mvTable_SizingFixedFit,
            ):
                FontRegistry.bind_to_item(dpg.last_item(), Font.BOLD)

    def _register_key_handler(self) -> None:
        with dpg.handler_registry(tag=TAG_SEQUENCER_ORDER_KEY_HANDLER):
            dpg.add_key_press_handler(callback=self._on_key_pressed)

    def update_order(self, view_model: SequencerOrderGridViewModel) -> None:
        """Reconciles the order table; rebuilds only when the position count changes."""
        cell_values = self._compute_cell_values(view_model)
        if view_model.position_count != self._position_count:
            self._rebuild_table(view_model, cell_values)
        else:
            self._order.reconcile(cell_values, self._render_cell)

        dpg_configure_item(TAG_SEQUENCER_ORDER_BUTTON_REMOVE, enabled=view_model.position_count > 0)

    def select_position(self, frame: int) -> None:
        """Moves the cursor to ``frame`` to follow the tracker, without re-driving it."""
        cursor = self._input_state.cursor
        if cursor is not None and cursor.position == frame:
            return

        generator = cursor.generator if cursor is not None else ORDER_ROWS[0]
        new_state = OrderInputState(cursor=OrderCursor(generator, frame))
        if 0 <= frame < self._position_count:
            self._apply_state(new_state, notify=False)
        else:
            self._input_state = new_state

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_ORDER_PANEL, enabled=enabled)

    def _compute_cell_values(self, view_model: SequencerOrderGridViewModel) -> Dict[OrderKey, str]:
        cell_values: Dict[OrderKey, str] = {}
        for position in range(view_model.position_count):
            cell_values[(None, position)] = view_model.master_label(position)
            for generator in GeneratorName.items():
                cell_values[(generator, position)] = view_model.entry_label(generator, position)

        return cell_values

    def _rebuild_table(self, view_model: SequencerOrderGridViewModel, cell_values: Dict[OrderKey, str]) -> None:
        dpg_delete_children(TAG_SEQUENCER_ORDER_TABLE, slot=0)
        dpg_delete_children(TAG_SEQUENCER_ORDER_TABLE, slot=1)
        self._order.reset(cell_values)
        self._position_count = view_model.position_count
        self._build_columns(view_model.position_count)
        for generator in ORDER_ROWS:
            self._build_row(generator, view_model.position_count)
        self._restore_cursor()

    def _build_columns(self, position_count: int) -> None:
        dpg.add_table_column(
            label="",
            parent=TAG_SEQUENCER_ORDER_TABLE,
            width_fixed=True,
            init_width_or_weight=self._layout.table_cells.generator,
        )
        for position in range(position_count):
            dpg.add_table_column(
                label=display_index(position),
                parent=TAG_SEQUENCER_ORDER_TABLE,
                width_fixed=True,
                init_width_or_weight=self._layout.order.position_column_width,
            )

    def _build_row(self, generator: Optional[GeneratorName], position_count: int) -> None:
        font = Font.BOLD_SMALL if generator is None else Font.REGULAR_SMALL
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_ORDER_TABLE)

        label_cell = dpg.add_table_cell(parent=row_id)
        label_text = dpg.add_text(self._row_labels[generator], parent=label_cell)
        FontRegistry.bind_to_item(label_text, font)

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
            self._order.register(key, selectable)

    def _render_cell(self, key: OrderKey) -> str:
        cursor = self._input_state.cursor
        if cursor is not None and (cursor.generator, cursor.position) == key:
            return active_label(self._input_state.pending, INDEX_DIGITS)

        return self._order.values.get(key, _EMPTY_LABEL)

    def _table_row(self, generator: Optional[GeneratorName]) -> int:
        return ORDER_ROWS.index(generator)

    def _apply_cursor_highlight(self, cursor: OrderCursor) -> None:
        for generator in ORDER_ROWS:
            color = self._layout.colors.cell_cursor if generator == cursor.generator else self._layout.colors.cursor_row
            dpg.highlight_table_cell(
                TAG_SEQUENCER_ORDER_TABLE,
                self._table_row(generator),
                cursor.position + 1,
                color=color,
            )

    def _remove_cursor_highlight(self, cursor: OrderCursor) -> None:
        for generator in ORDER_ROWS:
            dpg.unhighlight_table_cell(
                TAG_SEQUENCER_ORDER_TABLE,
                self._table_row(generator),
                cursor.position + 1,
            )

    def _restore_cursor(self) -> None:
        cursor = self._input_state.cursor
        if cursor is None or self._position_count == 0:
            self._input_state = OrderInputState()
            return

        position = min(cursor.position, self._position_count - 1)
        clamped = OrderCursor(cursor.generator, position)
        self._input_state = OrderInputState(cursor=clamped)
        self._apply_cursor_highlight(clamped)

    def _apply_state(self, new_state: OrderInputState, notify: bool = True) -> None:
        old = self._input_state.cursor
        new = new_state.cursor

        if old is not None:
            self._remove_cursor_highlight(old)

        self._input_state = new_state

        if old is not None:
            self._update_cell_display(old)

        if new is not None:
            self._apply_cursor_highlight(new)
            self._update_cell_display(new)

        if notify and new is not None and (old is None or old.position != new.position):
            self.call(self.on_frame_selected, new.position)

    def _update_cell_display(self, cursor: OrderCursor) -> None:
        key: OrderKey = (cursor.generator, cursor.position)
        widget = self._order.widget(key)
        if widget is not None:
            dpg.configure_item(widget, label=self._render_cell(key))

    def _on_cell_clicked(self, sender: Sender, app_data: bool, user_data: OrderKey) -> None:
        dpg.set_value(sender, False)
        generator, position = user_data
        self._apply_state(OrderInputState(cursor=OrderCursor(generator, position)))

    def _on_key_pressed(self, sender: Sender, app_data: int) -> None:
        if not dpg.is_item_hovered(TAG_SEQUENCER_ORDER_WINDOW):
            return

        if self._input_state.cursor is None:
            return

        match app_data:
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
            case dpg.mvKey_Escape:
                self._apply_state(self._input_state.cancel())
            case _:
                self._handle_printable_key(app_data)

    def _move_position(self, delta: int) -> None:
        self._apply_state(self._committed_state().navigate_position(delta, self._position_count))

    def _jump_position(self, index: int) -> None:
        self._apply_state(self._committed_state().navigate_position(index, self._position_count, absolute=True))

    def _move_channel(self, delta: int) -> None:
        self._apply_state(self._committed_state().navigate_channel(delta))

    def _committed_state(self) -> OrderInputState:
        state, index = self._input_state.commit_partial()
        if index is not None:
            self._emit_edit(self._input_state.cursor, index)

        return state

    def _handle_printable_key(self, key: int) -> None:
        char = HEX_KEYS.get(key)
        if char is None:
            return

        new_state, index = self._input_state.type_char(char)
        if index is not None:
            self._emit_edit(self._input_state.cursor, index)
            new_state = new_state.navigate_position(1, self._position_count)

        self._apply_state(new_state)

    def _emit_edit(self, cursor: Optional[OrderCursor], index: int) -> None:
        if cursor is None:
            return

        if cursor.generator is None:
            self.call(self.on_set_master_entry, cursor.position, index)
        else:
            self.call(self.on_set_order_entry, cursor.generator, cursor.position, index)

    def _on_add_clicked(self) -> None:
        self.call(self.on_add_requested)

    def _on_remove_clicked(self) -> None:
        cursor = self._input_state.cursor
        if cursor is not None and 0 <= cursor.position < self._position_count:
            self.call(self.on_remove_requested, cursor.position)
