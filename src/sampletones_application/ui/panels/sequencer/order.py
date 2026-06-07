from typing import Callable, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerOrderElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_ORDER_PANEL,
    TAG_SEQUENCER_ORDER_TABLE,
    TAG_SEQUENCER_ORDER_WINDOW,
)
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.utils.dpg import dpg_delete_children
from sampletones_application.view_model.sequencer.order import OrderEntryViewModel, SequencerOrderViewModel
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_index, display_pattern_label
from sampletones_shared.types.application import Sender

_NUM_CHANNELS = len(GeneratorName.items())


class GUISequencerOrderPanel(GUIPanel):
    """Compact horizontal table showing the pattern arrangement for all channels.

    Each column represents one shared order position; rows map to the four NES
    channels. Clicking any position column fires ``on_frame_selected`` so the
    tracker grid can jump to that position.
    """

    def __init__(
        self,
        *,
        layout: SequencerLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._layout = layout
        self._max_positions: int = 0
        self._current_frame: int = 0

        self.on_frame_selected: Optional[Callable[[int], None]] = None

        self._lbl_order = language_manager[
            Page.SEQUENCER,
            Panel.ORDER,
            TextType.LABEL,
            SequencerOrderElements.ORDER_TEXT,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_ORDER_PANEL,
            parent=TAG_SEQUENCER_GRID_PANEL,
        )

    def create_panel(self) -> None:
        with dpg.group(tag=self.tag, parent=self.parent):
            dpg.add_separator(parent=self.tag)
            header_text = dpg.add_text(self._lbl_order, parent=self.tag)
            FontRegistry.bind_to_item(header_text, Font.BOLD)
            self._create_order_window()

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

    def update_order(self, view_models: Tuple[SequencerOrderViewModel, ...]) -> None:
        """Rebuilds the order table columns and rows for the current position count.

        Uses explicit ``parent`` parameters throughout: the browser panel
        rebuilds its tree on a worker thread and shares the DearPyGui
        container stack, so implicit ``with`` blocks in the update path
        would race with it.
        """
        dpg_delete_children(TAG_SEQUENCER_ORDER_TABLE, slot=0)
        dpg_delete_children(TAG_SEQUENCER_ORDER_TABLE, slot=1)

        max_length = max((len(vm.entries) for vm in view_models), default=0)
        self._max_positions = max_length

        entries_by_generator: Dict[GeneratorName, Dict[int, OrderEntryViewModel]] = {
            view_model.generator: {entry.position: entry for entry in view_model.entries} for view_model in view_models
        }

        dpg.add_table_column(
            label="",
            parent=TAG_SEQUENCER_ORDER_TABLE,
            width_fixed=True,
            init_width_or_weight=self._layout.table_cells.generator,
        )
        for position in range(max_length):
            dpg.add_table_column(
                label=display_index(position),
                parent=TAG_SEQUENCER_ORDER_TABLE,
                width_fixed=True,
                init_width_or_weight=self._layout.order.position_column_width,
            )

        for generator in GeneratorName.items():
            self._build_channel_row(generator, entries_by_generator, max_length)

        if 0 <= self._current_frame < self._max_positions:
            self._highlight_column(self._current_frame)

    def select_position(self, frame: int) -> None:
        """Updates the highlighted column without rebuilding the table."""
        self._apply_highlight(frame)
        self._current_frame = frame

    def _build_channel_row(
        self,
        generator: GeneratorName,
        entries_by_gen: Dict[GeneratorName, Dict[int, OrderEntryViewModel]],
        max_length: int,
    ) -> None:
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_ORDER_TABLE)

        label_cell = dpg.add_table_cell(parent=row_id)
        label_text = dpg.add_text(generator.capitalized, parent=label_cell)
        FontRegistry.bind_to_item(label_text, Font.REGULAR_SMALL)

        for position in range(max_length):
            pos_cell = dpg.add_table_cell(parent=row_id)
            entry = entries_by_gen.get(generator, {}).get(position)
            cell_label = display_pattern_label(entry.pattern_label if entry is not None else None)
            selectable = dpg.add_selectable(
                parent=pos_cell,
                label=cell_label,
                user_data=position,
                callback=self._on_position_clicked,
            )
            FontRegistry.bind_to_item(selectable, Font.REGULAR_SMALL)

    def _apply_highlight(self, frame: int) -> None:
        if self._current_frame < self._max_positions:
            self._unhighlight_column(self._current_frame)
        if 0 <= frame < self._max_positions:
            self._highlight_column(frame)

    def _highlight_column(self, position: int) -> None:
        col = position + 1  # +1 for the channel label column
        for row_idx in range(_NUM_CHANNELS):
            dpg.highlight_table_cell(
                TAG_SEQUENCER_ORDER_TABLE,
                row_idx,
                col,
                color=self._layout.colors.pattern_highlight,
            )

    def _unhighlight_column(self, position: int) -> None:
        col = position + 1
        for row_idx in range(_NUM_CHANNELS):
            dpg.unhighlight_table_cell(TAG_SEQUENCER_ORDER_TABLE, row_idx, col)

    def _on_position_clicked(self, sender: Sender, app_data: bool, user_data: int) -> None:
        dpg.set_value(sender, False)
        self.call(self.on_frame_selected, user_data)
