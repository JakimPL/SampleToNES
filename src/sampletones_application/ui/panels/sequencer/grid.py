from typing import Callable, Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerGridElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_HANDLER_KEY,
    SUF_HANDLER_REGISTRY,
    SUF_PANEL_CENTER,
    TAG_GLOBAL_TAB_SEQUENCER,
)
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_GRID_TABLE_TRACKER,
    TAG_SEQUENCER_GRID_WINDOW_TRACKER,
)
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.panels.sequencer import display as tracker_display
from sampletones_application.ui.panels.sequencer.display import CellValues
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.edit import ClearAction, EditAction
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.input.subcolumn import SubColumn
from sampletones_application.ui.themes.tables.pattern import PatternTableTheme
from sampletones_application.utils.dpg import dpg_delete_children
from sampletones_application.view_model.sequencer.grid import (
    SequencerGridViewModel,
    SequencerRowViewModel,
)
from sampletones_application.view_model.sequencer.samples import SequencerSamplesViewModel
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_index
from sampletones_shared.types.application import Sender

_COLUMNS: Final[Tuple[Optional[GeneratorName], ...]] = (None,) + tuple(GeneratorName.items())

_HEX_KEYS: Final[Dict[int, str]] = {dpg.mvKey_0 + i: str(i) for i in range(10)} | {
    dpg.mvKey_A + i: "0123456789ABCDEF"[10 + i] for i in range(6)
}

OnClearRowCallback = Callable[[int, Optional[GeneratorName]], None]
OnSetRowCallback = Callable[[int, Optional[GeneratorName], Optional[str], Optional[int], Optional[int]], None]
OnCellSelectedCallback = Callable[[int, Optional[GeneratorName]], None]


class GUISequencerGridPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: SequencerLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._layout = layout
        self._language_manager = language_manager

        widths = layout.tracker.subcolumn_widths
        self._subcolumn_widths: Dict[SubColumn, int] = {
            SubColumn.INSTRUMENT: widths.instrument,
            SubColumn.TRANSPOSE: widths.transpose,
            SubColumn.VOLUME: widths.volume,
        }

        self._item_handler_tag = f"{TAG_SEQUENCER_GRID_PANEL}{SUF_HANDLER_REGISTRY}"
        self._key_handler_tag = f"{TAG_SEQUENCER_GRID_PANEL}{SUF_HANDLER_KEY}"

        self._rows: Dict[Optional[int], Sender] = {}
        self._cells: Dict[Tuple[int, Optional[GeneratorName], SubColumn], Sender] = {}
        self._cell_values: CellValues = {}
        self._current_row_count: int = 0
        self._highlighted_row: Optional[int] = None
        self._input_state: TrackerInputState = TrackerInputState()
        self._subcolumn_themes: Dict[SubColumn, int] = {}
        self._current_samples: Optional[SequencerSamplesViewModel] = None

        self.on_clear_row: Optional[OnClearRowCallback] = None
        self.on_set_row: Optional[OnSetRowCallback] = None
        self.on_cell_selected: Optional[OnCellSelectedCallback] = None

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
            pass

    def create_tracker(self) -> None:
        self._create_subcolumn_themes()
        self._create_tracker_view()

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_hover_handler(
                parent=self._item_handler_tag,
                callback=self._on_row_hovered,
            )
        with dpg.handler_registry(tag=self._key_handler_tag):
            dpg.add_key_press_handler(
                parent=self._key_handler_tag,
                callback=self._on_key_pressed,
            )

    def _create_subcolumn_themes(self) -> None:
        subcolumn_colors = self._layout.colors.subcolumns
        theme_colors = {
            SubColumn.INSTRUMENT: subcolumn_colors.instrument,
            SubColumn.TRANSPOSE: subcolumn_colors.transpose,
            SubColumn.VOLUME: subcolumn_colors.volume,
        }
        for subcolumn, color in theme_colors.items():
            with dpg.theme() as theme:
                with dpg.theme_component(dpg.mvSelectable):
                    dpg.add_theme_color(
                        dpg.mvThemeCol_Text,
                        color,
                        category=dpg.mvThemeCat_Core,
                    )

            self._subcolumn_themes[subcolumn] = theme

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
        """Rebuilds the tracker body from scratch for the visible order frame."""
        dpg_delete_children(TAG_SEQUENCER_GRID_TABLE_TRACKER, slot=1)
        self._set_rows(view_model)
        self._build_table(view_model)
        self._update_cursor()

    def _set_rows(self, view_model: SequencerGridViewModel) -> None:
        self._cell_values = {}
        for row in view_model.rows:
            self._set_instrument_cell(row)
            for generator in GeneratorName.items():
                self._set_channel_cell(row, generator)

    def _set_instrument_cell(self, row: SequencerRowViewModel) -> None:
        self._cell_values[(row.index, None, SubColumn.INSTRUMENT)] = row.sample_label
        self._cell_values[(row.index, None, SubColumn.TRANSPOSE)] = tracker_display.default_label(SubColumn.TRANSPOSE)
        self._cell_values[(row.index, None, SubColumn.VOLUME)] = tracker_display.default_label(SubColumn.VOLUME)

    def _set_channel_cell(
        self,
        row: SequencerRowViewModel,
        generator: GeneratorName,
    ) -> None:
        for subcolumn in SubColumn:
            self._set_subcolumn_cell(
                row,
                generator,
                subcolumn,
            )

    def _set_subcolumn_cell(
        self,
        row: SequencerRowViewModel,
        generator: GeneratorName,
        subcolumn: SubColumn,
    ) -> None:
        key = row.index, generator, subcolumn
        self._cell_values[key] = tracker_display.cell_display(
            row.cells[generator],
            subcolumn,
        )

    def _build_table(self, view_model: SequencerGridViewModel) -> None:
        self._rows = {}
        self._cells = {}
        self._current_row_count = len(view_model.rows)
        for row in view_model.rows:
            self._build_table_row(row)

    def _build_table_row(self, row: SequencerRowViewModel) -> None:
        """Builds one tracker row with explicit parents."""
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
            callback=self._on_row_number_clicked,
        )
        FontRegistry.bind_to_item(selectable, Font.REGULAR_SMALL)
        dpg.bind_item_handler_registry(selectable, self._item_handler_tag)
        self._rows[row.index] = selectable

        for generator in _COLUMNS:
            font = Font.BOLD_SMALL if generator is None else Font.REGULAR_SMALL
            cell = dpg.add_table_cell(parent=row_id)
            group = dpg.add_group(horizontal=True, horizontal_spacing=0, parent=cell)
            for subcolumn in SubColumn:
                subcolumn_selectable = dpg.add_selectable(
                    parent=group,
                    label=tracker_display.subcolumn_label(
                        row.index,
                        generator,
                        subcolumn,
                        cursor=self._input_state.cursor,
                        pending=self._input_state.pending,
                        cell_values=self._cell_values,
                    ),
                    width=self._subcolumn_widths[subcolumn],
                    user_data=(row.index, generator, subcolumn),
                    callback=self._on_cell_clicked,
                )
                FontRegistry.bind_to_item(subcolumn_selectable, font)
                dpg.bind_item_theme(subcolumn_selectable, self._subcolumn_themes[subcolumn])
                self._cells[(row.index, generator, subcolumn)] = subcolumn_selectable

    def _update_cursor(self) -> None:
        cursor = self._input_state.cursor
        if cursor is not None:
            if cursor.row < self._current_row_count:
                self._apply_cell_highlight(cursor.row, cursor.generator)
            else:
                self._input_state = TrackerInputState()

    def select_cell(self, row_index: int, generator: Optional[GeneratorName]) -> None:
        new_state = TrackerInputState(
            cursor=TrackerCursor(row_index, generator, SubColumn.INSTRUMENT),
            pending="",
        )
        self._apply_state(new_state)

    def deselect_cell(self) -> None:
        cursor = self._input_state.cursor
        if cursor is not None:
            self._remove_cell_highlight(cursor.row, cursor.generator)
            self._input_state = TrackerInputState()

    def _apply_state(self, new_state: TrackerInputState) -> None:
        old_cursor = self._input_state.cursor
        new_cursor = new_state.cursor

        old_pos = (old_cursor.row, old_cursor.generator) if old_cursor is not None else None
        new_pos = (new_cursor.row, new_cursor.generator) if new_cursor is not None else None

        if old_pos != new_pos and old_cursor is not None:
            self._remove_cell_highlight(old_cursor.row, old_cursor.generator)

        self._input_state = new_state

        if old_cursor is not None:
            self._update_cell_display(old_cursor.row, old_cursor.generator)

        if new_cursor is not None:
            if old_pos != new_pos:
                self._apply_cell_highlight(new_cursor.row, new_cursor.generator)
            self._update_cell_display(new_cursor.row, new_cursor.generator)

        if new_pos != old_pos and new_cursor is not None:
            if self.on_cell_selected is not None:
                self.on_cell_selected(new_cursor.row, new_cursor.generator)

    def update_samples(self, view_model: SequencerSamplesViewModel) -> None:
        self._current_samples = view_model

    def _update_cell_display(self, row: int, generator: Optional[GeneratorName]) -> None:
        for subcolumn in SubColumn:
            cell_id = self._cells.get((row, generator, subcolumn))
            if cell_id is not None:
                dpg.configure_item(
                    cell_id,
                    label=tracker_display.subcolumn_label(
                        row,
                        generator,
                        subcolumn,
                        cursor=self._input_state.cursor,
                        pending=self._input_state.pending,
                        cell_values=self._cell_values,
                    ),
                )

    def _resolve_sample_id(self, sample_index: int) -> Optional[str]:
        if self._current_samples is None:
            return None

        samples = self._current_samples.samples
        if sample_index < len(samples):
            return samples[sample_index].sample_id

        return None

    def _column_index(self, generator: Optional[GeneratorName]) -> int:
        return _COLUMNS.index(generator) + 2

    def _handle_edit_action(self, action: EditAction) -> None:
        row, generator = action.row, action.generator
        sample_id: Optional[str] = None
        if action.sample_idex is not None:
            self._cell_values[(row, generator, SubColumn.INSTRUMENT)] = tracker_display.format_committed(
                SubColumn.INSTRUMENT,
                action.sample_idex,
            )
            sample_id = self._resolve_sample_id(action.sample_idex)
        if action.transpose is not None:
            self._cell_values[(row, generator, SubColumn.TRANSPOSE)] = tracker_display.format_committed(
                SubColumn.TRANSPOSE,
                action.transpose,
            )
        if action.volume is not None:
            self._cell_values[(row, generator, SubColumn.VOLUME)] = tracker_display.format_committed(
                SubColumn.VOLUME,
                action.volume,
            )

        self.call(
            self.on_set_row,
            row,
            generator,
            sample_id,
            action.transpose,
            action.volume,
        )

    def _handle_clear_action(self, action: ClearAction) -> None:
        for subcolumn in SubColumn:
            self._cell_values.pop((action.row, action.generator, subcolumn), None)

        self.call(self.on_clear_row, action.row, action.generator)

    def _apply_cell_highlight(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        dpg.highlight_table_row(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
            color=self._layout.colors.cursor_row,
        )
        column_index = self._column_index(generator)
        dpg.highlight_table_cell(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
            column_index,
            color=self._layout.colors.cell_cursor,
        )

    def _remove_cell_highlight(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        dpg.unhighlight_table_row(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
        )
        col_idx = self._column_index(generator)
        dpg.unhighlight_table_cell(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            row_index,
            col_idx,
        )

    def _on_cell_clicked(
        self,
        sender: Sender,
        app_data: bool,
        user_data: Tuple[int, Optional[GeneratorName], SubColumn],
    ) -> None:
        dpg.set_value(sender, False)
        row_index, generator, subcolumn = user_data
        new_state = TrackerInputState(
            cursor=TrackerCursor(row_index, generator, subcolumn),
            pending="",
        )
        self._apply_state(new_state)

    def _on_key_pressed(self, sender: Sender, app_data: int) -> None:
        if self._input_state.cursor is None:
            return

        cursor = self._input_state.cursor
        match app_data:
            case dpg.mvKey_Up:
                self._apply_state(self._committed_state().navigate_row(-1, self._current_row_count))
            case dpg.mvKey_Down:
                self._apply_state(self._committed_state().navigate_row(1, self._current_row_count))
            case dpg.mvKey_Left:
                self._apply_state(self._committed_state().navigate_subcolumn(-1))
            case dpg.mvKey_Right:
                self._apply_state(self._committed_state().navigate_subcolumn(1))
            case dpg.mvKey_Tab:
                current_idx = _COLUMNS.index(cursor.generator)
                delta = -1 if (dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)) else 1
                next_idx = (current_idx + delta) % len(_COLUMNS)
                self._apply_state(self._committed_state().navigate_column(_COLUMNS[next_idx]))
            case dpg.mvKey_Home:
                self._apply_state(self._committed_state().navigate_row(0, self._current_row_count, absolute=True))
            case dpg.mvKey_End:
                self._apply_state(
                    self._committed_state().navigate_row(
                        self._current_row_count - 1, self._current_row_count, absolute=True
                    )
                )
            case dpg.mvKey_Prior:
                self._apply_state(
                    self._committed_state().navigate_row(-self._layout.tracker.page_size, self._current_row_count)
                )
            case dpg.mvKey_Next:
                self._apply_state(
                    self._committed_state().navigate_row(self._layout.tracker.page_size, self._current_row_count)
                )
            case dpg.mvKey_Return:
                self._apply_state(self._committed_state().navigate_subcolumn(1))
            case dpg.mvKey_Delete:
                state, clear_action = self._input_state.clear()
                self._handle_clear_action(clear_action)
                self._apply_state(state.navigate_subcolumn(1))
            case dpg.mvKey_Back:
                state, clear_action = self._input_state.clear()
                self._handle_clear_action(clear_action)
                self._apply_state(state.navigate_subcolumn(-1))
            case dpg.mvKey_Escape:
                self._apply_state(self._input_state.cancel())
            case _:
                self._handle_printable_key(app_data)

    def _committed_state(self) -> TrackerInputState:
        state, edit_action = self._input_state.commit_partial()
        if edit_action is not None:
            self._handle_edit_action(edit_action)
        return state

    def _handle_printable_key(self, key: int) -> None:
        char = _HEX_KEYS.get(key)
        if char is None:
            return
        new_state, edit_action = self._input_state.type_char(char)
        if edit_action is not None:
            self._handle_edit_action(edit_action)
            new_state = new_state.navigate_subcolumn(1)
        self._apply_state(new_state)

    def _on_row_number_clicked(self, sender: Sender, app_data: bool, user_data: int) -> None:
        dpg.set_value(sender, False)
        self.select_cell(user_data, None)

    def _on_row_hovered(self, sender: Sender, app_data: int) -> None:
        if not dpg.does_item_exist(app_data):
            return

        row_index = dpg.get_item_user_data(app_data)
        if row_index is not None:
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
