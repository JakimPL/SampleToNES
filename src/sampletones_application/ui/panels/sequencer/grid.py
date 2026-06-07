from typing import Callable, Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerGridElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_HANDLER_REGISTRY,
    SUF_PANEL_CENTER,
    TAG_GLOBAL_TAB_SEQUENCER,
)
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_GRID_PANEL_PLAYER,
    TAG_SEQUENCER_GRID_TABLE_TRACKER,
    TAG_SEQUENCER_GRID_WINDOW_TRACKER,
)
from sampletones_application.layout.player import PlayerLayout
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.panels.player import GUIAudioPlayerPanel
from sampletones_application.ui.themes.tables.pattern import PatternTableTheme
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.view_model.sequencer.grid import (
    SequencerGridViewModel,
    SequencerRowViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_index
from sampletones_shared.types.application import Sender

_SAMPLE_COLUMN_IDX: Final[int] = 2
_GENERATOR_COLUMN_IDX: Final[Dict[GeneratorName, int]] = {
    generator: 3 + index for index, generator in enumerate(GeneratorName.items())
}


class GUISequencerGridPanel(GUIPanel):
    def __init__(
        self,
        sequencer_grid_logic: SequencerGridLogic,
        player_logic: PlayerLogic,
        *,
        layout: SequencerLayout,
        layout_player: PlayerLayout,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self.sequencer_grid_logic = sequencer_grid_logic
        self._player_logic = player_logic
        self._layout = layout
        self._layout_player = layout_player
        self._language_manager = language_manager
        self._dialogs = dialogs

        self.player_panel: GUIAudioPlayerPanel

        self._item_handler_tag = f"{TAG_SEQUENCER_GRID_PANEL}{SUF_HANDLER_REGISTRY}"
        self._key_handler_tag = f"{TAG_SEQUENCER_GRID_PANEL}_key_handler"
        self._rows: Dict[Optional[int], Sender] = {}
        self._highlighted_row: Optional[int] = None
        self._selected_cell: Optional[Tuple[int, Optional[GeneratorName]]] = None

        self.on_navigate: Optional[Callable[[int, int], None]] = None
        self.on_clear_row: Optional[Callable[[int, Optional[GeneratorName]], None]] = None
        self.on_edit_cell: Optional[Callable[[int, Optional[GeneratorName]], None]] = None
        self.on_set_row: Optional[
            Callable[[int, Optional[GeneratorName], Optional[str], Optional[int], Optional[int]], None]
        ] = None

        self.pattern_theme = PatternTableTheme()

        self._lbl_tracker = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.TRACKER_TEXT,
        ]
        self._lbl_col_row = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_ROW,
        ]
        self._lbl_col_sample = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_SAMPLE,
        ]
        self._lbl_col_pulse_1 = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_PULSE_1,
        ]
        self._lbl_col_pulse_2 = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_PULSE_2,
        ]
        self._lbl_col_triangle = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_TRIANGLE,
        ]
        self._lbl_col_noise = language_manager[
            Page.SEQUENCER,
            Panel.GRID,
            TextType.LABEL,
            SequencerGridElements.COLUMN_NOISE,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_GRID_PANEL,
            parent=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_CENTER}",
            height=-1,
        )

    def create_panel(self) -> None:
        self._setup_handlers()
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_audio_panel()

    def create_tracker(self) -> None:
        self._create_tracker_view()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_hover_handler(
                parent=self._item_handler_tag,
                callback=self._on_item_hovered,
            )
            dpg.add_item_clicked_handler(
                parent=self._item_handler_tag,
                callback=self._on_item_hovered,
            )
        with dpg.handler_registry(tag=self._key_handler_tag):
            dpg.add_key_press_handler(
                parent=self._key_handler_tag,
                callback=self._on_key_pressed,
            )

    def _create_audio_panel(self) -> None:
        self.player_panel = GUIAudioPlayerPanel(
            tag=TAG_SEQUENCER_GRID_PANEL_PLAYER,
            parent=TAG_SEQUENCER_GRID_PANEL,
            player_logic=self._player_logic,
            layout=self._layout_player,
            language_manager=self._language_manager,
            dialogs=self._dialogs,
        )

    def _create_tracker_view(self) -> None:
        dpg.add_separator(parent=self.tag)
        section_text = dpg.add_text(self._lbl_tracker, parent=self.tag)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

        with dpg.child_window(
            tag=TAG_SEQUENCER_GRID_WINDOW_TRACKER,
            parent=self.tag,
            width=0,
            height=-1,
        ):
            with dpg.table(
                tag=TAG_SEQUENCER_GRID_TABLE_TRACKER,
                width=0,
                header_row=True,
                resizable=False,
                borders_innerH=False,
                borders_innerV=True,
                borders_outerH=True,
                borders_outerV=True,
                scrollX=True,
                scrollY=True,
                row_background=True,
                policy=dpg.mvTable_SizingFixedFit,
            ):
                FontRegistry.bind_to_item(dpg.last_item(), Font.BOLD)
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(
                    label=self._lbl_col_row,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.row,
                )
                dpg.add_table_column(
                    label=self._lbl_col_sample,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.sample,
                )
                dpg.add_table_column(
                    label=self._lbl_col_pulse_1,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.generator,
                )
                dpg.add_table_column(
                    label=self._lbl_col_pulse_2,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.generator,
                )
                dpg.add_table_column(
                    label=self._lbl_col_triangle,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.generator,
                )
                dpg.add_table_column(
                    label=self._lbl_col_noise,
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.generator,
                )
                dpg.add_table_column(width_stretch=True)

        self.pattern_theme.bind_to_item(TAG_SEQUENCER_GRID_TABLE_TRACKER)

    def update_grid(self, view_model: SequencerGridViewModel) -> None:
        """Rebuilds the tracker body from scratch for the visible order frame.

        Patterns vary in length, so rows are recreated rather than mutated in
        place; the table columns (slot 0) are kept and only the row slot is
        cleared.
        """
        dpg.delete_item(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            children_only=True,
            slot=1,
        )
        self._rows = {}
        for row in view_model.rows:
            self._build_table_row(row)

        if self._selected_cell is not None:
            row_index, generator = self._selected_cell
            if row_index in self._rows:
                self._apply_cell_highlight(row_index, generator)
            else:
                self._selected_cell = None

    def _build_table_row(self, row: SequencerRowViewModel) -> None:
        """Builds one tracker row with explicit parents.

        Every item passes an explicit ``parent`` instead of relying on ``with``
        container blocks: the tree browser populates on a worker thread, and the
        implicit DearPyGui container stack is process-global, so nested ``with``
        blocks here would race with that concurrent building.
        """
        row_id = dpg.add_table_row(
            parent=TAG_SEQUENCER_GRID_TABLE_TRACKER,
            user_data=row.index,
        )

        spacer_cell = dpg.add_table_cell(parent=row_id)
        dpg.add_spacer(parent=spacer_cell, width=0)

        number_cell = dpg.add_table_cell(parent=row_id)
        selectable = dpg.add_selectable(
            parent=number_cell,
            label=display_index(row.index),
            span_columns=True,
            user_data=row.index,
        )
        FontRegistry.bind_to_item(selectable, Font.REGULAR_SMALL)
        dpg.bind_item_handler_registry(selectable, self._item_handler_tag)
        self._rows[row.index] = selectable

        sample_cell = dpg.add_table_cell(parent=row_id)
        sample_text = dpg.add_selectable(
            parent=sample_cell,
            label=row.sample_label,
            user_data=(row.index, None),
            callback=self._on_cell_clicked,
        )
        FontRegistry.bind_to_item(sample_text, Font.BOLD_SMALL)

        for generator in GeneratorName.items():
            generator_cell = dpg.add_table_cell(parent=row_id)
            cell_text = dpg.add_selectable(
                parent=generator_cell,
                label=row.cells[generator].label,
                user_data=(row.index, generator),
                callback=self._on_cell_clicked,
            )
            FontRegistry.bind_to_item(cell_text, Font.REGULAR_SMALL)

    def select_cell(self, row_index: int, generator: Optional[GeneratorName]) -> None:
        self._remove_cell_highlight()
        self._selected_cell = (row_index, generator)
        self._apply_cell_highlight(row_index, generator)

    def deselect_cell(self) -> None:
        self._remove_cell_highlight()
        self._selected_cell = None

    def show_instrument_picker(self, row_index: int, generator: Optional[GeneratorName]) -> None:
        """Open the instrument picker for the given cell. Implement the popup UX here."""

    def show_value_editor(self, row_index: int, generator: Optional[GeneratorName]) -> None:
        """Open the transpose/volume editor for the given cell. Implement the popup UX here."""

    def _apply_cell_highlight(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        col = _SAMPLE_COLUMN_IDX if generator is None else _GENERATOR_COLUMN_IDX[generator]
        dpg.highlight_table_cell(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
            col,
            color=self._layout.colors.cell_cursor,
        )

    def _remove_cell_highlight(self) -> None:
        if self._selected_cell is None:
            return

        row_index, generator = self._selected_cell
        col = _SAMPLE_COLUMN_IDX if generator is None else _GENERATOR_COLUMN_IDX[generator]
        dpg.unhighlight_table_cell(TAG_SEQUENCER_GRID_TABLE_TRACKER, row_index, col)

    def _on_cell_clicked(
        self,
        sender: Sender,
        app_data: bool,
        user_data: Tuple[int, Optional[GeneratorName]],
    ) -> None:
        dpg.set_value(sender, False)
        row_index, generator = user_data
        self.select_cell(row_index, generator)

    def _on_key_pressed(self, sender: Sender, app_data: int) -> None:
        if self._selected_cell is None:
            pass

    def _on_item_hovered(self, sender: Sender, app_data: int) -> None:
        if not dpg.does_item_exist(app_data):
            return

        row_index = dpg.get_item_user_data(app_data)
        if row_index is not None:
            dpg.set_value(app_data, False)
            highlighted_item = self._rows.get(self._highlighted_row)
            if highlighted_item is not None:
                dpg.set_value(highlighted_item, False)

            self._highlighted_row = row_index

    def highlight_row(self, row_index: Optional[int] = None) -> None:
        self.unhighlight_row(self._highlighted_row)
        self._highlighted_row = row_index
        if row_index is None:
            return

        dpg.highlight_table_row(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
            color=self._layout.colors.pattern_highlight,
        )

    def unhighlight_row(self, row_index: Optional[int] = None) -> None:
        if row_index is None:
            return

        dpg.unhighlight_table_row(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
        )
        self._highlighted_row = None
