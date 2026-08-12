from typing import Callable, Dict, Final, FrozenSet, Optional, Set, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerOrderElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.layout.general.plus_minus_buttons import (
    PlusMinusButtonsLayout,
)
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HANDLER_DRAG,
    SUF_HANDLER_HEADER,
    SUF_HANDLER_REGISTRY,
)
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_ORDER_BUTTON_PAIR,
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
from sampletones_application.ui.elements.plus_minus_buttons import (
    GUIPlusMinusButtons,
    PlusMinusOrder,
)
from sampletones_application.ui.elements.table.caret import CaretOverlay
from sampletones_application.ui.elements.table.cells import EditableCells, pending_label
from sampletones_application.ui.elements.table.selection import TableSelection
from sampletones_application.ui.panels.sequencer.channels import (
    ChannelMenuLabels,
    ChannelSwitch,
    channel_tooltip,
)
from sampletones_application.ui.panels.sequencer.columns import channel_color
from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures
from sampletones_application.ui.panels.sequencer.grid.surface.clipboard import (
    BlockShortcuts,
    ClipboardItems,
)
from sampletones_application.ui.panels.sequencer.grid.surface.edit import GridEditSurface
from sampletones_application.ui.panels.sequencer.input.order import (
    INDEX_DIGITS,
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.input.target import OrderTarget
from sampletones_application.ui.themes.inline import (
    create_header_selectable_theme,
    create_selectable_text_theme,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_delete_item
from sampletones_application.utils.gui.keyboard import (
    PRIORITY_PANEL,
    ActivePredicate,
    KeyEvent,
    KeyRouter,
)
from sampletones_application.utils.gui.keyboard.keys import HEX_KEYS
from sampletones_application.utils.gui.keyboard.modifiers import Modifier, capture_modifiers
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.palette.colors.faded import FadedColor
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_application.view_model.sequencer.move import MoveDirection
from sampletones_application.view_model.sequencer.order import (
    SequencerOrderTrackerViewModel,
)
from sampletones_application.view_model.sequencer.region import OrderCell, OrderRegion
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_id
from sampletones_shared.types.application import ColorRGBA, Sender
from sampletones_shared.types.callback import VoidCallback

OrderKey = Tuple[Optional[GeneratorName], int]

OnFrameSelectedCallback = Callable[[int], None]
OnRemoveCallback = Callable[[int], None]
OnFrameActionCallback = Callable[[int], None]
OnMoveCallback = Callable[[int, int], None]
OnSetOrderEntryCallback = Callable[[GeneratorName, int, Optional[int]], None]
OnSetMasterEntryCallback = Callable[[int, Optional[int]], None]
OnChannelMuteToggledCallback = Callable[[GeneratorName], None]
OnChannelSoloedCallback = Callable[[GeneratorName], None]
OnBlockRegionCallback = Callable[[OrderRegion], None]
OnPasteBlockCallback = Callable[[OrderCell], None]
CanPasteBlockQuery = Callable[[], bool]
OrderEditSurface = GridEditSurface[OrderCursor, OrderRegion, OrderCell, OrderTarget]

MOVE_DIRECTIONS: Final[Dict[ShortcutId, MoveDirection]] = {
    ShortcutId.ORDER_MOVE_FRAME_LEFT: MoveDirection.PREVIOUS,
    ShortcutId.ORDER_MOVE_FRAME_RIGHT: MoveDirection.NEXT,
    ShortcutId.ORDER_MOVE_FRAME_TO_START: MoveDirection.FIRST,
    ShortcutId.ORDER_MOVE_FRAME_TO_END: MoveDirection.LAST,
}

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
        plus_minus_layout: PlusMinusButtonsLayout,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        tab_active: ActivePredicate,
        shortcut_source: ShortcutSource,
        initial_collapsed: bool = False,
    ) -> None:
        self._layout = layout
        self._plus_minus_layout = plus_minus_layout
        self._router = key_router
        self._tab_active = tab_active
        self._shortcuts = shortcut_source
        self._buttons: Optional[GUIPlusMinusButtons] = None
        self._position_count: int = 0
        self._order: EditableCells[OrderKey] = EditableCells()
        self._input_state: OrderInputState = OrderInputState()
        self._selection: TableSelection[OrderKey] = TableSelection(
            cells=self._order,
            cell_at=self._cell_at,
            covered=self._selected_cells,
        )
        self._highlighted: Optional[OrderCursor] = None
        self._highlighted_column: Optional[int] = None
        self._current_position: Optional[int] = None
        self._playing_position: Optional[int] = None
        self._cell_handler_tag = compose_tag(TAG_SEQUENCER_ORDER_TABLE, SUF_HANDLER_REGISTRY)
        self._label_handler_tag = compose_tag(TAG_SEQUENCER_ORDER_TABLE, SUF_HANDLER_HEADER)
        self._drag_handler_tag = compose_tag(TAG_SEQUENCER_ORDER_TABLE, SUF_HANDLER_DRAG)
        self._label_rows: Dict[Sender, Optional[GeneratorName]] = {}
        self._entry_theme: int = 0
        self._muted_entry_theme: int = 0
        self._label_theme: int = 0
        self._muted_label_theme: int = 0
        self._current_channels: Optional[SequencerChannelsViewModel] = None
        self._table_theme = ThemeRegistry.get(TAG_SEQUENCER_THEME_TABLE_ORDER)

        self.on_frame_selected: Optional[OnFrameSelectedCallback] = None
        self.on_remove_requested: Optional[OnRemoveCallback] = None
        self.on_duplicate_requested: Optional[OnFrameActionCallback] = None
        self.on_clone_requested: Optional[OnFrameActionCallback] = None
        self.on_insert_requested: Optional[OnFrameActionCallback] = None
        self.on_clear_requested: Optional[OnFrameActionCallback] = None
        self.on_play_from_requested: Optional[OnFrameActionCallback] = None
        self.on_move_requested: Optional[OnMoveCallback] = None
        self.on_set_order_entry: Optional[OnSetOrderEntryCallback] = None
        self.on_set_master_entry: Optional[OnSetMasterEntryCallback] = None
        self.on_cell_selected: Optional[VoidCallback] = None
        self.on_copy_block: Optional[OnBlockRegionCallback] = None
        self.on_cut_block: Optional[OnBlockRegionCallback] = None
        self.on_delete_block: Optional[OnBlockRegionCallback] = None
        self.on_paste_block: Optional[OnPasteBlockCallback] = None
        self.can_paste_block: Optional[CanPasteBlockQuery] = None
        self.on_channel_mute_toggled: Optional[OnChannelMuteToggledCallback] = None
        self.on_channel_soloed: Optional[OnChannelSoloedCallback] = None
        self.on_channels_toggled: Optional[VoidCallback] = None
        self.on_channels_muted: Optional[VoidCallback] = None
        self.on_channels_unmuted: Optional[VoidCallback] = None

        self._blocks: BlockGestures[OrderRegion, OrderCell] = BlockGestures(grid=self)
        self._surface: OrderEditSurface = GridEditSurface.build(
            grid=self,
            blocks=self._blocks,
            target=OrderTarget,
            shortcuts=shortcut_source,
            block_shortcuts=BlockShortcuts(
                copy=ShortcutId.ORDER_COPY_BLOCK,
                cut=ShortcutId.ORDER_CUT_BLOCK,
                paste=ShortcutId.ORDER_PASTE_BLOCK,
            ),
            labels=ClipboardItems.labels(language_manager),
        )
        self._lbl_order = self._label(language_manager, SequencerOrderElements.ORDER_TEXT)
        self._load_row_labels(language_manager)
        self._load_context_labels(language_manager)
        self._load_label_tooltips(language_manager)
        self._create_channel_switch(language_manager)

        super().__init__(
            tag=TAG_SEQUENCER_ORDER_PANEL,
        )
        self._enable_vertical_collapse(
            initial_collapsed=initial_collapsed,
            auto_height=True,
            card_tag=TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD,
        )

    @staticmethod
    def _label(language_manager: LanguageManager, element: SequencerOrderElements) -> str:
        return language_manager[Page.SEQUENCER, Panel.ORDER, TextType.LABEL, element]

    def _load_row_labels(self, language_manager: LanguageManager) -> None:
        """Reads the name each row carries, which its label and its menu title show."""
        self._row_labels: Dict[Optional[GeneratorName], str] = {
            None: self._label(language_manager, SequencerOrderElements.ROW_MASTER),
            GeneratorName.PULSE1: self._label(language_manager, SequencerOrderElements.ROW_PULSE_1),
            GeneratorName.PULSE2: self._label(language_manager, SequencerOrderElements.ROW_PULSE_2),
            GeneratorName.TRIANGLE: self._label(language_manager, SequencerOrderElements.ROW_TRIANGLE),
            GeneratorName.NOISE: self._label(language_manager, SequencerOrderElements.ROW_NOISE),
        }

    def _load_context_labels(self, language_manager: LanguageManager) -> None:
        def label(element: SequencerOrderElements) -> str:
            return self._label(language_manager, element)

        self._lbl_context_play = label(SequencerOrderElements.CONTEXT_PLAY)
        self._lbl_context_duplicate = label(SequencerOrderElements.CONTEXT_DUPLICATE)
        self._lbl_context_clone = label(SequencerOrderElements.CONTEXT_CLONE)
        self._lbl_context_insert = label(SequencerOrderElements.CONTEXT_INSERT)
        self._lbl_context_clear = label(SequencerOrderElements.CONTEXT_CLEAR)
        self._lbl_context_remove = label(SequencerOrderElements.CONTEXT_REMOVE)
        self._lbl_context_move_left = label(SequencerOrderElements.CONTEXT_MOVE_LEFT)
        self._lbl_context_move_right = label(SequencerOrderElements.CONTEXT_MOVE_RIGHT)
        self._lbl_context_move_start = label(SequencerOrderElements.CONTEXT_MOVE_START)
        self._lbl_context_move_end = label(SequencerOrderElements.CONTEXT_MOVE_END)

    def _load_label_tooltips(self, language_manager: LanguageManager) -> None:
        """Reads the row-label tooltips, which name the click gestures the labels carry."""

        def tooltip(element: SequencerOrderElements) -> str:
            return language_manager[Page.SEQUENCER, Panel.ORDER, TextType.TOOLTIP, element]

        self._tooltip_label_channel = channel_tooltip(tooltip(SequencerOrderElements.LABEL_CHANNEL))
        self._tooltip_label_master = tooltip(SequencerOrderElements.LABEL_MASTER)

    def _create_channel_switch(self, language_manager: LanguageManager) -> None:
        """Builds the switch a row label's click and menu act through.

        The hooks are read at call time, so the switch is built here while they are still unset and
        the coordinator wires them once the panel exists.
        """
        labels = ChannelMenuLabels(
            mute=self._label(language_manager, SequencerOrderElements.CONTEXT_MUTE),
            unmute=self._label(language_manager, SequencerOrderElements.CONTEXT_UNMUTE),
            solo=self._label(language_manager, SequencerOrderElements.CONTEXT_SOLO),
            unsolo=self._label(language_manager, SequencerOrderElements.CONTEXT_UNSOLO),
            mute_all=self._label(language_manager, SequencerOrderElements.CONTEXT_MUTE_ALL),
            unmute_all=self._label(language_manager, SequencerOrderElements.CONTEXT_UNMUTE_ALL),
        )
        self._channel_switch = ChannelSwitch(
            labels=labels,
            on_mute_toggled=lambda generator: self.call(self.on_channel_mute_toggled, generator),
            on_soloed=lambda generator: self.call(self.on_channel_soloed, generator),
            on_toggled=lambda: self.call(self.on_channels_toggled),
            on_muted=lambda: self.call(self.on_channels_muted),
            on_unmuted=lambda: self.call(self.on_channels_unmuted),
        )

    def create_panel(self, parent: str) -> None:
        self._create_entry_themes()
        with (
            self._collapsible_card(
                parent,
                self._lbl_order,
                glyph=self._glyphs.headers.order,
            ),
            dpg.group(tag=self.tag),
        ):
            self._create_button_row()
            self._create_order_window()
            self._register_handlers()

    def _create_entry_themes(self) -> None:
        """Colours every pattern entry, in the shade its channel sounds and the shade it is silenced.

        The entry themes target only the selectable text, so they leave every other colour to the
        global theme; the dimmed variant keeps the entry colour at reduced alpha, so a silenced
        channel's frames stay readable and editable while the others are worked on. A row label
        carries the header's hover and press washes instead, so it reads as the switch it is.
        """
        colors = self._layout.colors
        self._entry_theme = create_selectable_text_theme(colors.text.order)
        self._muted_entry_theme = create_selectable_text_theme(
            FadedColor(
                color=colors.text.order,
                fraction=self._layout.tracker.muted_text_fraction,
            ),
        )
        self._label_theme = create_header_selectable_theme(
            colors.label,
            colors.header.hovered,
            colors.header.active,
        )
        self._muted_label_theme = create_header_selectable_theme(
            colors.muted.text,
            colors.header.hovered,
            colors.header.active,
        )

    def _create_button_row(self) -> None:
        buttons = GUIPlusMinusButtons(
            tag=TAG_SEQUENCER_ORDER_BUTTON_PAIR,
            parent=self.tag,
            layout=self._plus_minus_layout,
            order=PlusMinusOrder.PLUS_FIRST,
            hold_repeat=False,
            decrement_enabled=False,
        )
        buttons.on_increment = self._on_add_clicked
        buttons.on_decrement = self._on_remove_clicked
        self._buttons = buttons

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
            dpg.add_item_active_handler(callback=self._on_cell_held)

        with dpg.item_handler_registry(tag=self._label_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_label_right_clicked)

        with dpg.handler_registry(tag=self._drag_handler_tag):
            dpg.add_mouse_click_handler(
                button=dpg.mvMouseButton_Left,
                callback=self._on_pointer_pressed,
            )

    def update_order(self, view_model: SequencerOrderTrackerViewModel) -> None:
        """Reconciles the order table; rebuilds only when the position count changes."""
        cell_values = self._compute_cell_values(view_model)
        if view_model.position_count != self._position_count:
            self._rebuild_table(view_model, cell_values)
        else:
            self._order.reconcile(cell_values, self._render_cell)

        self._refresh_remove_enabled()

    def select_position(self, frame: int) -> None:
        """Follows the tracker frame: always updates the unfocused column highlight;
        also moves the edit cursor when one is active.
        """
        self._current_position = frame
        self._follow_frame(frame)
        self._refresh_remove_enabled()

    def _follow_frame(self, frame: int) -> None:
        """Carries the edit cursor to the frame, or shifts the unfocused column highlight to it
        while no cursor is set."""
        cursor = self._input_state.cursor
        if cursor is not None:
            if cursor.position == frame:
                return

            new_state = OrderInputState(
                cursor=OrderCursor(cursor.generator, frame),
            )
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
        self._selection.repaint()
        self._update_caret()

        if cursor is not None:
            self._update_cell_display(cursor)

        if self._current_position is not None and 0 <= self._current_position < self._position_count:
            self._apply_column_highlight(self._current_position, focused=False)

        self._refresh_remove_enabled()

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_ORDER_PANEL, enabled=enabled)

    def update_channels(self, view_model: SequencerChannelsViewModel) -> None:
        """Shows which channels the song player silences.

        The model is kept so a rebuilt table takes the cue again, the way the row tints do, and so
        a table still waiting for its rows picks it up once they arrive.
        """
        self._current_channels = view_model
        self._apply_channel_cues()

    def _apply_channel_cues(self) -> None:
        """Marks each silenced channel along its whole row: label, background, and entry text.

        The three cues land together because they read as one: the row recedes as a unit while its
        frames stay legible, so the channel is visibly out of the mix and still open for editing.
        The tracker grid carries the same cue down each column, so a channel looks the same in both.
        """
        if not dpg.does_item_exist(TAG_SEQUENCER_ORDER_TABLE):
            return

        self._tint_channel_rows()
        self._bind_label_themes()
        for generator in GeneratorName.items():
            self._bind_channel_entry_themes(generator)

    def _bind_label_themes(self) -> None:
        for label, generator in self._label_rows.items():
            muted = generator is not None and self._is_muted(generator)
            dpg.bind_item_theme(
                label,
                self._muted_label_theme if muted else self._label_theme,
            )

    def _bind_channel_entry_themes(self, generator: GeneratorName) -> None:
        theme = self._muted_entry_theme if self._is_muted(generator) else self._entry_theme
        for position in range(self._position_count):
            widget = self._order.widget((generator, position))
            if widget is not None:
                dpg.bind_item_theme(widget, theme)

    def _is_muted(self, generator: GeneratorName) -> bool:
        return self._current_channels is not None and self._current_channels.is_muted(generator)

    def _compute_cell_values(
        self,
        view_model: SequencerOrderTrackerViewModel,
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
        view_model: SequencerOrderTrackerViewModel,
        cell_values: Dict[OrderKey, str],
    ) -> None:
        """Recreates the whole table when the position count changes.

        Deleting and re-adding a live table's *columns* leaves DPG's per-column
        state (and any highlight keyed by column index) dangling, which corrupted
        the heap. Replacing the table item wholesale sidesteps that: the cursor and
        column highlights die with the old table, so nothing references freed
        columns. The selected cells go with them, and :meth:`_restore_cursor` brings the
        cursor back on its own — a table of another width is a table a region no longer
        describes.
        """
        dpg_delete_item(TAG_SEQUENCER_ORDER_TABLE)
        self._highlighted = None
        self._highlighted_column = None
        self._selection.reset()
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

        self._label_rows = {}
        for generator in CHANNEL_AXIS:
            self._build_row(generator, position_count)
            if generator is None:
                self._build_divider_row(position_count)

        self._apply_column_backgrounds()
        self._highlight_master_row(position_count)
        self._apply_channel_cues()

    def repaint(self) -> None:
        """Issues every tint the table holds as its own state.

        DearPyGui keeps a row, column or cell highlight on the table rather than on an item,
        so a colour reaches it only by being pushed again. Gathering the pushes here gives
        the palette one call to make and keeps a rebuilt table and a recoloured one identical.
        """
        if not dpg.does_item_exist(TAG_SEQUENCER_ORDER_TABLE):
            return

        self._apply_column_backgrounds()
        self._highlight_master_row(self._position_count)
        self._apply_channel_cues()
        self._repaint_highlights()

    def _repaint_highlights(self) -> None:
        if self._highlighted_column is not None:
            position = self._highlighted_column
            focused = self._input_state.cursor is not None and self._input_state.cursor.position == position
            self._apply_column_highlight(position, focused=focused)

        if self._highlighted is not None:
            self._apply_cursor_highlight(self._highlighted)

    def _apply_column_backgrounds(self) -> None:
        """Tints the label column like the header row.

        The position columns carry no static shade, so the per-channel row tints read
        cleanly beneath the position and cursor highlights — the transposed analog of
        the tracker grid, whose channel column tints sit beneath its cursor.
        """
        dpg.highlight_table_column(
            TAG_SEQUENCER_ORDER_TABLE,
            0,
            self._layout.colors.order.label.rgba,
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
                color=self._layout.colors.order.master_divider.rgba,
            )

    def _highlight_master_cell_at(self, column: int) -> None:
        dpg.highlight_table_cell(
            TAG_SEQUENCER_ORDER_TABLE,
            MASTER_TABLE_ROW,
            column,
            color=self._layout.colors.order.master.rgba,
        )

    def _tint_channel_rows(self) -> None:
        """Washes each channel row with a light tint of its identity colour.

        Uses a row highlight so it sits on a layer beneath the position and cursor
        highlights, which keep working; a cleared cursor cell falls back to the row
        tint. This is the transposed analog of the tracker grid's per-channel column
        tint, sharing the fraction. A silenced channel trades that identity for a
        neutral dark shade, so its row recedes as a whole.
        """
        for generator in GeneratorName.items():
            dpg.highlight_table_row(
                TAG_SEQUENCER_ORDER_TABLE,
                self._table_row(generator),
                self._channel_row_tint(generator),
            )

    def _channel_row_tint(self, generator: GeneratorName) -> ColorRGBA:
        if self._is_muted(generator):
            return self._layout.colors.muted.background.rgba

        channel = channel_color(self._layout.colors.channels, generator)
        return FadedColor(
            color=channel,
            fraction=self._layout.tracker.channel_column_tint,
        ).rgba

    def _apply_column_highlight(self, position: int, *, focused: bool) -> None:
        if focused:
            color = self._layout.colors.pattern_highlight
        elif position == self._playing_position:
            color = self._layout.colors.order.column_playing
        else:
            color = self._layout.colors.order.column_current

        dpg.highlight_table_column(TAG_SEQUENCER_ORDER_TABLE, position + 1, color.rgba)
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
        self._add_row_label(row_id, generator)
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

    def _add_row_label(
        self,
        row_id: Sender,
        generator: Optional[GeneratorName],
    ) -> None:
        """Places one clickable row label: a channel's mute target, or the master target.

        The label spans its frozen cell, which is what makes the whole name a click target, and it
        carries its channel so the click knows which row it landed on. A tooltip names the gestures
        the label answers to, and the right-click registry opens the same actions as a menu.
        """
        label_cell = dpg.add_table_cell(parent=row_id)
        label = dpg.add_selectable(
            parent=label_cell,
            label=self._row_labels[generator],
            user_data=generator,
            callback=self._on_label_clicked,
        )
        FontRegistry.bind_to_item(label, Font.MONO_BOLD_SMALL)
        dpg.bind_item_handler_registry(label, self._label_handler_tag)
        show_tooltip(
            label,
            self._tooltip_label_master if generator is None else self._tooltip_label_channel,
        )
        self._label_rows[label] = generator

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
        return CHANNEL_AXIS.index(generator) + 1

    def _apply_cursor_highlight(self, cursor: OrderCursor) -> None:
        dpg.highlight_table_cell(
            TAG_SEQUENCER_ORDER_TABLE,
            self._table_row(cursor.generator),
            cursor.position + 1,
            color=self._layout.colors.cell_cursor.rgba,
        )
        self._highlighted = cursor

    def _selected_cells(self) -> FrozenSet[OrderKey]:
        """Every cell the selection covers, clipped to the positions the table holds."""
        region = self._input_state.region
        if region is None:
            return frozenset()

        keys: Set[OrderKey] = set()
        for generator in region.generators:
            for position in region.positions:
                if position < self._position_count:
                    keys.add((generator, position))

        return frozenset(keys)

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

        self._selection.repaint()
        self._update_caret()
        self._refresh_remove_enabled()

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
        _app_data: bool,
        user_data: OrderKey,
    ) -> None:
        """Places the cursor on the clicked cell, or carries a selection out to it while Shift is held.

        A drag that comes back to the cell it started from ends on a click, and the selection takes
        that click as the end of the drag, so the range dragged out stands and the cursor with it.
        """
        if self._selection.claims_click(sender, user_data):
            return

        state = self._committed_state()
        generator, position = user_data
        cursor = OrderCursor(generator, position)
        if Modifier.SHIFT in capture_modifiers():
            self._apply_state(state.extend_to(cursor))
            return

        self._apply_state(OrderInputState(cursor=cursor))

    def _on_cell_held(self, _sender: Sender, app_data: Sender) -> None:
        """Carries the selection to the cell under a held pointer, which is what drags a range out.

        The gesture states how far the pointer has carried: a plain drag anchors at the cell the
        press landed on, and one whose press held Shift carries the selection already standing.
        """
        reach = self._selection.hold(app_data)
        if reach is None:
            return

        state = self._committed_state()
        if not reach.extends:
            state = OrderInputState(cursor=OrderCursor(*reach.origin))

        self._apply_state(state.extend_to(OrderCursor(*reach.reached)))

    def _on_pointer_pressed(self, _sender: Sender, _app_data: int) -> None:
        """Drops the gesture a finished drag left behind, so this press selects on its own.

        A press is where a gesture ends rather than the release before it, because the release
        reaches this panel ahead of the click the cell itself reports: a drag that comes back to
        the cell it started from would otherwise have its selection taken down by its own click.
        """
        self._selection.drop_gesture()

    def _cell_at(self) -> Optional[OrderKey]:
        """The cell the pointer stands on, clamped to the table the order lays out.

        A drag that runs past an edge reads as the edge itself, so carrying the pointer beyond
        the last channel or the last position selects up to it rather than stopping there.
        """
        left, top = dpg.get_mouse_pos(local=False)
        position = self._position_at(left)
        if position is None:
            return None

        return (self._generator_at(top), position)

    def _generator_at(self, top: float) -> Optional[GeneratorName]:
        """Which channel row stands at a height, the master row reading ``None``.

        The master row stands apart from the channels beneath it, so the walk asks each row where
        it was drawn and takes the first one reaching past the pointer.
        """
        for generator in CHANNEL_AXIS:
            widget = self._order.widget((generator, 0))
            if widget is None:
                continue

            _, row_top = dpg.get_item_rect_min(widget)
            _, row_height = dpg.get_item_rect_size(widget)
            if top < row_top + row_height:
                return generator

        return CHANNEL_AXIS[-1]

    def _position_at(self, left: float) -> Optional[int]:
        """Which position stands at a width, counted from the first cell's left edge.

        Every position column is the same width, so the count is arithmetic once two of them
        state the pitch; an order of a single position holds every width there is.
        """
        first = self._cell_left(0)
        if first is None:
            return None

        following = self._cell_left(1)
        if following is None:
            return 0

        position = int((left - first) // (following - first))
        return max(0, min(position, self._position_count - 1))

    def _cell_left(self, position: int) -> Optional[float]:
        """Where a position column's cells begin, in the coordinates the viewport is drawn in."""
        widget = self._order.widget((None, position))
        if widget is None:
            return None

        cell_left, _ = dpg.get_item_rect_min(widget)
        return float(cell_left)

    def _on_cell_right_clicked(
        self,
        _sender: Sender,
        app_data: Tuple[int, int],
    ) -> None:
        """Opens the frame-operations menu for the right-clicked cell.

        The menu acts on the clicked cell and its frame directly, and leaves the edit cursor (and,
        while following playback, the playhead) where it is — right-clicking should not seek.
        """
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        key = dpg.get_item_user_data(clicked_item)
        if key is None:
            return

        generator, position = key
        self._show_context_menu(generator, position)

    def _on_label_clicked(
        self,
        sender: Sender,
        _app_data: bool,
        user_data: Optional[GeneratorName],
    ) -> None:
        self._channel_switch.click(sender, user_data)

    def _on_label_right_clicked(
        self,
        _sender: Sender,
        app_data: Tuple[int, int],
    ) -> None:
        """Opens the channel menu for the right-clicked row label.

        The registry reaches the row labels alone, so a click on one of them names its row through
        the map the rows filled in; a label replaced by a rebuild is absent from it.
        """
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        if clicked_item not in self._label_rows:
            return

        self._show_channel_menu(self._label_rows[clicked_item])

    def _show_channel_menu(self, generator: Optional[GeneratorName]) -> None:
        """Opens the menu behind a row label, titled with the row's own name."""
        with context_menu():
            header = dpg.add_text(self._row_labels[generator])
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            self._channel_switch.add_menu_items(generator, self._current_channels)

    def _show_context_menu(
        self,
        generator: Optional[GeneratorName],
        position: int,
    ) -> None:
        target = self._surface.target_at(OrderCursor(generator, position))
        with context_menu():
            header = dpg.add_text(display_id(position))
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            add_play_menu_item(
                self._lbl_context_play,
                lambda: self.call(self.on_play_from_requested, position),
                shortcut=self._shortcuts.display(ShortcutId.PLAY_FROM_FRAME),
            )
            dpg.add_separator()
            self.add_action_items(target)

    @property
    def edit_surface(self) -> OrderEditSurface:
        """This table as the menu bar's Edit menu reaches it."""
        return self._surface

    def input_state(self) -> OrderInputState:
        """Where the cursor stands and what it has selected, which a target is resolved from."""
        return self._input_state

    def owns_keys(self) -> bool:
        """Whether the table owns the next key, which is also what the Edit menu asks."""
        return self._keys_active()

    def add_action_items(self, target: OrderTarget) -> None:
        """Builds every action an order cell offers, in the order each menu prints them.

        The table states its actions once, and whoever asks for them decides where they are shown:
        the cell menu asks for the cell a pointer landed on, and the menu bar asks for the cell the
        cursor stands on. An action added here reaches both.
        """
        self._surface.add_block_items(target)
        dpg.add_separator()
        self._add_frame_items(target.cell.position)
        dpg.add_separator()
        self._add_move_items(target.cell.position)

    def _add_frame_items(self, position: int) -> None:
        """Builds the frame operations, each acting on the whole frame the target cell sits in."""
        dpg.add_menu_item(
            label=self._lbl_context_duplicate,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_DUPLICATE_FRAME),
            callback=lambda: self.call(self.on_duplicate_requested, position),
        )
        dpg.add_menu_item(
            label=self._lbl_context_clone,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_CLONE_FRAME),
            callback=lambda: self.call(self.on_clone_requested, position),
        )
        dpg.add_menu_item(
            label=self._lbl_context_insert,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_INSERT_FRAME),
            callback=lambda: self.call(self.on_insert_requested, position),
        )
        dpg.add_menu_item(
            label=self._lbl_context_clear,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_CLEAR_FRAME),
            callback=lambda: self.call(self.on_clear_requested, position),
        )
        dpg.add_menu_item(
            label=self._lbl_context_remove,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_REMOVE_FRAME),
            callback=lambda: self.call(self.on_remove_requested, position),
        )

    def _add_move_items(self, position: int) -> None:
        """Builds the four moves a frame can make, in the order they walk the song."""
        self._add_move_item(
            self._lbl_context_move_left,
            ShortcutId.ORDER_MOVE_FRAME_LEFT,
            position,
        )
        self._add_move_item(
            self._lbl_context_move_right,
            ShortcutId.ORDER_MOVE_FRAME_RIGHT,
            position,
        )
        self._add_move_item(
            self._lbl_context_move_start,
            ShortcutId.ORDER_MOVE_FRAME_TO_START,
            position,
        )
        self._add_move_item(
            self._lbl_context_move_end,
            ShortcutId.ORDER_MOVE_FRAME_TO_END,
            position,
        )

    def _add_move_item(
        self,
        label: str,
        shortcut_id: ShortcutId,
        position: int,
    ) -> None:
        """Adds a move item, greyed out (disabled) when the move would have no effect.

        The action names both the direction it moves and the accelerator it prints, so the item a
        reader sees is the one the key press performs.
        """
        target = MOVE_DIRECTIONS[shortcut_id].target(position, self._position_count)
        dpg.add_menu_item(
            label=label,
            shortcut=self._shortcuts.display(shortcut_id),
            enabled=target is not None,
            callback=lambda: self.call(self.on_move_requested, position, target),
        )

    def _keys_active(self) -> bool:
        """Whether the order table owns the next key: its tab is in front, its cursor is set, and
        no field holds the keyboard.

        The table keeps its cursor while another tab is worked on, so the tab in front is what
        decides whether a press reaches it. A focused field keeps the keyboard, so the table stands
        down while the user types into an input. A modal dialog claims keys at a higher priority in
        the router, so the table carries no modal check of its own.
        """
        return self._tab_active() and self._input_state.cursor is not None and not self._router.is_field_focused

    def _on_key_pressed(self, event: KeyEvent) -> bool:
        """Applies an order key to the active cell, reporting whether the table consumed it.

        The scheme says which press each order action answers to; a press the order category
        leaves unnamed goes to cell entry, which keeps the hex digits and hands the rest to the
        application's global shortcuts.
        """
        cursor = self._input_state.cursor
        if cursor is None:
            return False

        shortcut_id = self._shortcuts.action(ShortcutCategory.ORDER, event)
        if shortcut_id is None:
            return self._type_character(event)

        if self._move_cursor(shortcut_id):
            return True

        if self._extend_selection(shortcut_id):
            return True

        if self._block_action(shortcut_id):
            return True

        if self._edit_cell(shortcut_id):
            return True

        return self._act_on_frame(shortcut_id, cursor.position)

    def _move_cursor(self, shortcut_id: ShortcutId) -> bool:
        """Moves the edit cursor over the table, reporting whether the action was one of its moves."""
        match shortcut_id:
            case ShortcutId.ORDER_PREVIOUS_POSITION:
                self._move_position(-1)
            case ShortcutId.ORDER_NEXT_POSITION:
                self._move_position(1)
            case ShortcutId.ORDER_PREVIOUS_CHANNEL:
                self._move_channel(-1)
            case ShortcutId.ORDER_NEXT_CHANNEL:
                self._move_channel(1)
            case ShortcutId.ORDER_FIRST_POSITION:
                self._jump_position(0)
            case ShortcutId.ORDER_LAST_POSITION:
                self._jump_position(self._position_count - 1)
            case _:
                return False

        return True

    def _extend_selection(self, shortcut_id: ShortcutId) -> bool:
        """Grows or shrinks the selected block, reporting whether the action was one of its reaches.

        Each reach moves the end the cursor holds while the anchor stays where the selection began,
        so the same keys that move the cursor select with Shift held.
        """
        match shortcut_id:
            case ShortcutId.ORDER_EXTEND_SELECTION_UP:
                self._extend_channel(-1)
            case ShortcutId.ORDER_EXTEND_SELECTION_DOWN:
                self._extend_channel(1)
            case ShortcutId.ORDER_EXTEND_SELECTION_LEFT:
                self._extend_position(-1)
            case ShortcutId.ORDER_EXTEND_SELECTION_RIGHT:
                self._extend_position(1)
            case ShortcutId.ORDER_EXTEND_SELECTION_TO_FIRST_POSITION:
                self._extend_to_position(0)
            case ShortcutId.ORDER_EXTEND_SELECTION_TO_LAST_POSITION:
                self._extend_to_position(self._position_count - 1)
            case _:
                return False

        return True

    def _block_action(self, shortcut_id: ShortcutId) -> bool:
        """Acts on the selected block, reporting whether the action was one of its gestures.

        Delete is a block gesture only while a selection stands: with one it empties every cell the
        selection covers and keeps it, and with none it falls through to clearing the cell under
        the cursor, the meaning that key already carries.
        """
        match shortcut_id:
            case ShortcutId.ORDER_COPY_BLOCK:
                self._surface.copy()
            case ShortcutId.ORDER_CUT_BLOCK:
                self._surface.cut()
            case ShortcutId.ORDER_CLEAR_CELL if self._input_state.region is not None:
                self._surface.delete()
            case ShortcutId.ORDER_PASTE_BLOCK:
                self._surface.paste()
            case _:
                return False

        return True

    def _edit_cell(self, shortcut_id: ShortcutId) -> bool:
        """Empties the cell under the cursor or drops a partial entry, reporting whether the action
        was one of the cell edits.

        A cancel with nothing typed and nothing selected leaves the press to the application, so
        Escape stops playback while the table holds a cursor.
        """
        match shortcut_id:
            case ShortcutId.ORDER_CLEAR_CELL:
                self._clear_cell()
                self._move_position(1)
            case ShortcutId.ORDER_CLEAR_PREVIOUS_CELL:
                self._clear_cell()
                self._move_position(-1)
            case ShortcutId.ORDER_CANCEL_ENTRY:
                if not self._input_state.pending and self._input_state.anchor is None:
                    return False

                self._apply_state(self._input_state.cancel())
            case _:
                return False

        return True

    def _act_on_frame(self, shortcut_id: ShortcutId, position: int) -> bool:
        """Adds, removes or moves a whole frame, reporting whether the action was one of them.

        A move with nowhere to go still counts as consumed, so a press at either boundary stays
        out of the global shortcuts.
        """
        direction = MOVE_DIRECTIONS.get(shortcut_id)
        if direction is not None:
            target = direction.target(position, self._position_count)
            if target is not None:
                self.call(self.on_move_requested, position, target)

            return True

        match shortcut_id:
            case ShortcutId.ORDER_ADD_FRAME:
                self._on_add_clicked()
            case ShortcutId.ORDER_INSERT_FRAME:
                self.call(self.on_insert_requested, position)
            case ShortcutId.ORDER_REMOVE_FRAME:
                self._on_remove_clicked()
            case ShortcutId.ORDER_DUPLICATE_FRAME:
                self.call(self.on_duplicate_requested, position)
            case ShortcutId.ORDER_CLONE_FRAME:
                self.call(self.on_clone_requested, position)
            case ShortcutId.ORDER_CLEAR_FRAME:
                self.call(self.on_clear_requested, position)
            case _:
                return False

        return True

    def _move_position(self, delta: int) -> None:
        self._apply_state(
            self._committed_state().navigate_position(
                delta,
                self._position_count,
            ),
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

    def _extend_position(self, delta: int) -> None:
        self._apply_state(
            self._committed_state().extend_position(
                delta,
                self._position_count,
            ),
        )

    def _extend_to_position(self, index: int) -> None:
        self._apply_state(
            self._committed_state().extend_position(
                index,
                self._position_count,
                absolute=True,
            ),
        )

    def _extend_channel(self, delta: int) -> None:
        self._apply_state(self._committed_state().extend_channel(delta))

    def _committed_state(self) -> OrderInputState:
        state, index = self._input_state.commit_partial()
        if index is not None:
            self._emit(self._input_state.cursor, index)

        return state

    def commit_entry(self) -> None:
        """Writes the entry being typed into the cell the cursor stands on.

        A block gesture takes this first, so what it lifts out carries the index the reader has
        just finished typing.
        """
        self._apply_state(self._committed_state())

    def _type_character(self, event: KeyEvent) -> bool:
        """Types a hex digit into the cell under the cursor, reporting whether the press was one.

        A press holding Ctrl or Alt is an application gesture, so cell entry reads the plain keys
        and leaves the rest to the global shortcuts.
        """
        if Modifier.CTRL in event.modifiers or Modifier.ALT in event.modifiers:
            return False

        char = HEX_KEYS.get(event.key)
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

    def _get_removable_position(self) -> Optional[int]:
        """The frame ``[-]`` acts on: the cursor's frame, or the followed tracker frame while no
        cursor is set, resolved while it addresses a live frame.
        """
        position = self._get_cursor_position()
        if position is not None and 0 <= position < self._position_count:
            return position

        return None

    def _refresh_remove_enabled(self) -> None:
        """Enables ``[-]`` while a press would remove a frame, so a greyed-out button tells the
        user that removal awaits a selected frame.
        """
        if self._buttons is not None:
            self._buttons.set_decrement_enabled(self._get_removable_position() is not None)

    def _on_add_clicked(self) -> None:
        """Inserts an empty frame after the current one (appends when at or past the end)."""
        position = self._get_cursor_position()
        if position is None or not 0 <= position < self._position_count:
            position = self._position_count - 1

        self.call(self.on_insert_requested, position)

    def _on_remove_clicked(self) -> None:
        position = self._get_removable_position()
        if position is not None:
            self.call(self.on_remove_requested, position)
