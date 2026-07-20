from typing import Callable, Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerGridElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_GRID_GROUP_TRACKER,
    TAG_SEQUENCER_GRID_PANEL,
    TAG_SEQUENCER_GRID_TABLE_TRACKER,
    TAG_SEQUENCER_GRID_WINDOW_TRACKER,
    TAG_SEQUENCER_THEME_TABLE_PATTERN,
)
from sampletones_application.ui.elements.context_menu import (
    add_play_menu_item,
    context_menu,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.table.caret import CaretOverlay
from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer import display as tracker_display
from sampletones_application.ui.panels.sequencer.columns import (
    DIVIDER_TABLE_COLUMN,
    SAMPLE_TABLE_COLUMN,
    channel_color,
    tracker_table_column,
)
from sampletones_application.ui.panels.sequencer.display import CellKey, CellValues
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.edit import (
    ClearAction,
    EditAction,
)
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.themes.inline import create_selectable_text_theme
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_delete_children
from sampletones_application.utils.gui.keyboard import (
    PRIORITY_PANEL,
    KeyEvent,
    KeyRouter,
)
from sampletones_application.utils.gui.shortcuts.keys import HEX_KEYS, SIGN_KEYS, Modifier
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_application.view_model.sequencer.grid import (
    SequencerGridViewModel,
    SequencerRowViewModel,
)
from sampletones_application.view_model.sequencer.samples import (
    SequencerSamplesViewModel,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.utils.display import NOTE_OFF, display_id
from sampletones_shared.constants.music import OCTAVE_SEMITONES, SEMITONE_STEP
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.color import with_alpha_fraction

OnClearRowCallback = Callable[[int, Optional[GeneratorName]], None]
OnClearSubcolumnCallback = Callable[[int, Optional[GeneratorName], SubColumn], None]
OnSetRowCallback = Callable[[int, Optional[GeneratorName], Optional[str], Optional[int], Optional[int]], None]
OnSetNoteOffCallback = Callable[[int, Optional[GeneratorName]], None]
OnCellSelectedCallback = Callable[[int, Optional[GeneratorName]], None]
OnPlayFromRowCallback = Callable[[int], None]
OnPlayFromFrameCallback = Callable[[], None]
OnAdjustCallback = Callable[[int, Optional[GeneratorName], int], None]


VOLUME_FINE_STEP: Final[int] = 1
VOLUME_COARSE_STEP: Final[int] = (MAX_VOLUME + 1) // 4

FROZEN_HEADER_ROWS: Final[int] = 1


class GUISequencerGridPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: SequencerLayout,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        initial_collapsed: bool = False,
    ) -> None:
        self._layout = layout
        self._language_manager = language_manager
        self._router = key_router

        widths = layout.tracker.subcolumn_widths
        self._subcolumn_widths: Dict[SubColumn, int] = {
            SubColumn.INSTRUMENT: widths.instrument,
            SubColumn.TRANSPOSE: widths.transpose,
            SubColumn.VOLUME: widths.volume,
        }

        self._item_handler_tag = f"{TAG_SEQUENCER_GRID_PANEL}{SUF_HANDLER_REGISTRY}"
        self._cell_handler_tag = f"{TAG_SEQUENCER_GRID_TABLE_TRACKER}{SUF_HANDLER_REGISTRY}"

        self._rows: Dict[Optional[int], Sender] = {}
        self._editable_cells: EditableCells[CellKey] = EditableCells()
        self._current_row_count: int = 0
        self._highlighted_row: Optional[int] = None
        self._playing_row: Optional[int] = None
        self._input_state: TrackerInputState = TrackerInputState()
        self._subcolumn_themes: Dict[SubColumn, int] = {}
        self._row_number_theme: int = 0
        self._current_samples: Optional[SequencerSamplesViewModel] = None

        self.on_clear_row: Optional[OnClearRowCallback] = None
        self.on_clear_subcolumn: Optional[OnClearSubcolumnCallback] = None
        self.on_set_row: Optional[OnSetRowCallback] = None
        self.on_set_note_off: Optional[OnSetNoteOffCallback] = None
        self.on_cell_selected: Optional[OnCellSelectedCallback] = None
        self.on_play_from_row: Optional[OnPlayFromRowCallback] = None
        self.on_play_from_frame: Optional[OnPlayFromFrameCallback] = None
        self.on_adjust_transpose: Optional[OnAdjustCallback] = None
        self.on_adjust_volume: Optional[OnAdjustCallback] = None

        self.pattern_theme = ThemeRegistry.get(TAG_SEQUENCER_THEME_TABLE_PATTERN)

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

        self._column_labels: Dict[Optional[GeneratorName], str] = {
            None: self._lbl_col_sample,
            GeneratorName.PULSE1: self._lbl_col_pulse_1,
            GeneratorName.PULSE2: self._lbl_col_pulse_2,
            GeneratorName.TRIANGLE: self._lbl_col_triangle,
            GeneratorName.NOISE: self._lbl_col_noise,
        }

        self._load_context_labels(language_manager)

        self._sc_play_from_here = Shortcut(
            dpg.mvKey_Spacebar,
            (Modifier.CTRL, Modifier.SHIFT),
        ).get_display_string()
        self._sc_play_from_frame = Shortcut(dpg.mvKey_Spacebar, (Modifier.CTRL,)).get_display_string()

        super().__init__(
            tag=TAG_SEQUENCER_GRID_PANEL,
            height=-1,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def _load_context_labels(self, language_manager: LanguageManager) -> None:
        def label(element: SequencerGridElements) -> str:
            return language_manager[Page.SEQUENCER, Panel.GRID, TextType.LABEL, element]

        self._lbl_context_play = label(SequencerGridElements.CONTEXT_PLAY)
        self._lbl_context_play_from_frame = label(SequencerGridElements.CONTEXT_PLAY_FROM_FRAME)
        self._lbl_context_note_off = label(SequencerGridElements.CONTEXT_NOTE_OFF)
        self._lbl_context_set_instrument = label(SequencerGridElements.CONTEXT_SET_INSTRUMENT)
        self._lbl_context_no_samples = label(SequencerGridElements.CONTEXT_NO_SAMPLES)
        self._lbl_context_clear_subcolumn = label(SequencerGridElements.CONTEXT_CLEAR_SUBCOLUMN)
        self._lbl_context_clear_cell = label(SequencerGridElements.CONTEXT_CLEAR_CELL)
        self._lbl_context_clear_row = label(SequencerGridElements.CONTEXT_CLEAR_ROW)
        self._lbl_context_transpose_up = label(SequencerGridElements.CONTEXT_TRANSPOSE_UP)
        self._lbl_context_transpose_down = label(SequencerGridElements.CONTEXT_TRANSPOSE_DOWN)
        self._lbl_context_transpose_octave_up = label(SequencerGridElements.CONTEXT_TRANSPOSE_OCTAVE_UP)
        self._lbl_context_transpose_octave_down = label(SequencerGridElements.CONTEXT_TRANSPOSE_OCTAVE_DOWN)
        self._lbl_context_volume_up = label(SequencerGridElements.CONTEXT_VOLUME_UP)
        self._lbl_context_volume_down = label(SequencerGridElements.CONTEXT_VOLUME_DOWN)
        self._lbl_context_volume_up_coarse = label(SequencerGridElements.CONTEXT_VOLUME_UP_COARSE)
        self._lbl_context_volume_down_coarse = label(SequencerGridElements.CONTEXT_VOLUME_DOWN_COARSE)

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        self._create_subcolumn_themes()
        self._create_tracker_view(parent)

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_hover_handler(
                parent=self._item_handler_tag,
                callback=self._on_row_hovered,
            )
        with dpg.item_handler_registry(tag=self._cell_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_cell_right_clicked)
        self._router.register(
            self._on_key_pressed,
            priority=PRIORITY_PANEL,
            active=self._keys_active,
        )

    def _create_subcolumn_themes(self) -> None:
        subcolumn_colors = self._layout.colors.text
        theme_colors = {
            SubColumn.INSTRUMENT: subcolumn_colors.instrument,
            SubColumn.TRANSPOSE: subcolumn_colors.transpose,
            SubColumn.VOLUME: subcolumn_colors.volume,
        }
        for subcolumn, color in theme_colors.items():
            self._subcolumn_themes[subcolumn] = create_selectable_text_theme(color)

        self._row_number_theme = create_selectable_text_theme(self._layout.colors.text.row)

    def _create_tracker_view(self, parent: str) -> None:
        with self._collapsible_card(parent, self._lbl_tracker, glyph=self._glyphs.headers.tracker):
            dpg.add_group(tag=TAG_SEQUENCER_GRID_GROUP_TRACKER)
            with dpg.child_window(
                tag=TAG_SEQUENCER_GRID_WINDOW_TRACKER,
                parent=TAG_SEQUENCER_GRID_GROUP_TRACKER,
                border=False,
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
                    scrollX=False,
                    scrollY=True,
                    freeze_rows=FROZEN_HEADER_ROWS,
                    row_background=True,
                    policy=dpg.mvTable_SizingFixedFit,
                ):
                    FontRegistry.bind_to_item(dpg.last_item(), Font.MONO_BOLD)
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
                        width_fixed=True,
                        init_width_or_weight=self._layout.table_cells.divider,
                        no_header_label=True,
                    )
                    for generator in GeneratorName.items():
                        dpg.add_table_column(
                            label=self._column_labels[generator],
                            width_fixed=True,
                            init_width_or_weight=self._layout.table_cells.generator,
                        )
                    dpg.add_table_column(width_stretch=True)

        self.pattern_theme.bind_to_item(TAG_SEQUENCER_GRID_TABLE_TRACKER)

    def update_grid(self, view_model: SequencerGridViewModel) -> None:
        """Reconciles the tracker body with the visible order frame.

        The grid is only torn down and rebuilt when the row count changes; for the
        common in-place edit the changed cell labels are reconfigured one by one.
        Reusing the existing widgets preserves scroll position, the hover row, and
        the edit cursor that a full rebuild would otherwise discard.
        """
        cell_values = self._compute_cell_values(view_model)
        if len(view_model.rows) != self._current_row_count:
            self._rebuild_table(view_model, cell_values)
        else:
            self._editable_cells.reconcile(cell_values, self._render_cell)

    def _rebuild_table(
        self,
        view_model: SequencerGridViewModel,
        cell_values: CellValues,
    ) -> None:
        dpg_delete_children(TAG_SEQUENCER_GRID_TABLE_TRACKER, slot=1)
        self._editable_cells.reset(cell_values)
        self._build_table(view_model)
        self._highlight_sample_column()
        self._tint_channel_columns()
        self._update_cursor()
        self._apply_playing_row_highlight()

    def _render_cell(self, key: CellKey) -> str:
        row, generator, subcolumn = key
        return tracker_display.subcolumn_label(
            row,
            generator,
            subcolumn,
            cursor=self._input_state.cursor,
            pending=self._input_state.pending,
            cell_values=self._editable_cells.values,
        )

    def _highlight_sample_column(self) -> None:
        """Tints the sample column and the rule that separates it from the channels.

        These column highlights are static decoration, distinct from the cursor's
        cell/row highlight; reapplying them after each rebuild keeps them in place
        once the rows are replaced.
        """
        dpg.highlight_table_column(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            SAMPLE_TABLE_COLUMN,
            self._layout.colors.sample.column,
        )
        dpg.highlight_table_column(
            TAG_SEQUENCER_GRID_TABLE_TRACKER,
            DIVIDER_TABLE_COLUMN,
            self._layout.colors.sample.divider,
        )

    def _tint_channel_columns(self) -> None:
        """Washes each channel's column with a faint tint of its identity colour.

        Reapplied after each rebuild alongside the sample column so the tint survives
        row replacement, giving the tracker the same per-channel identity the order
        table carries in its row labels.
        """
        channels = self._layout.colors.channels
        fraction = self._layout.tracker.channel_column_tint
        for generator in GeneratorName.items():
            tint = with_alpha_fraction(channel_color(channels, generator), fraction)
            dpg.highlight_table_column(
                TAG_SEQUENCER_GRID_TABLE_TRACKER,
                tracker_table_column(generator),
                tint,
            )

    def _compute_cell_values(
        self,
        view_model: SequencerGridViewModel,
    ) -> CellValues:
        cell_values: CellValues = {}
        for row in view_model.rows:
            cell_values[(row.index, None, SubColumn.INSTRUMENT)] = row.sample_instrument
            cell_values[(row.index, None, SubColumn.TRANSPOSE)] = row.sample_transpose
            cell_values[(row.index, None, SubColumn.VOLUME)] = row.sample_volume
            for generator in GeneratorName.items():
                cell = row.cells[generator]
                for subcolumn in SubColumn:
                    cell_values[
                        (
                            row.index,
                            generator,
                            subcolumn,
                        )
                    ] = tracker_display.cell_display(
                        cell,
                        subcolumn,
                    )

        return cell_values

    def _build_table(self, view_model: SequencerGridViewModel) -> None:
        self._rows = {}
        self._current_row_count = len(view_model.rows)
        for row in view_model.rows:
            self._build_table_row(row)

    def _build_table_row(self, row: SequencerRowViewModel) -> None:
        """Builds one tracker row.

        The cells are positional, so the empty divider cell after the sample column
        keeps the channel cells aligned with their (shifted) table columns.
        """
        row_id = dpg.add_table_row(
            parent=TAG_SEQUENCER_GRID_TABLE_TRACKER,
            user_data=row.index,
        )
        self._add_empty_cell(row_id)
        self._add_row_number_cell(row_id, row.index)
        self._add_column_cell(row_id, row.index, None)
        self._add_empty_cell(row_id)
        for generator in GeneratorName.items():
            self._add_column_cell(row_id, row.index, generator)

    def _add_empty_cell(self, row_id: Sender) -> None:
        empty_cell = dpg.add_table_cell(parent=row_id)
        if dpg.does_item_exist(empty_cell):
            dpg.add_spacer(parent=empty_cell, width=0)

    def _add_row_number_cell(self, row_id: Sender, row_index: int) -> None:
        number_cell = dpg.add_table_cell(parent=row_id)
        selectable = dpg.add_selectable(
            parent=number_cell,
            label=display_id(row_index),
            user_data=row_index,
            callback=self._on_row_number_clicked,
        )
        FontRegistry.bind_to_item(selectable, Font.MONO_SMALL)
        dpg.bind_item_theme(selectable, self._row_number_theme)
        dpg.bind_item_handler_registry(selectable, self._item_handler_tag)
        self._rows[row_index] = selectable

    def _add_column_cell(
        self,
        row_id: Sender,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        font = Font.MONO_BOLD_SMALL if generator is None else Font.MONO_SMALL
        cell = dpg.add_table_cell(parent=row_id)
        group = dpg.add_group(
            horizontal=True,
            horizontal_spacing=0,
            parent=cell,
        )
        for subcolumn in SubColumn:
            self._add_subcolumn_selectable(
                group,
                row_index,
                generator,
                subcolumn,
                font,
            )

    def _add_subcolumn_selectable(
        self,
        group: Sender,
        row_index: int,
        generator: Optional[GeneratorName],
        subcolumn: SubColumn,
        font: Font,
    ) -> None:
        key = (row_index, generator, subcolumn)
        selectable = dpg.add_selectable(
            parent=group,
            label=self._render_cell(key),
            width=self._subcolumn_widths[subcolumn],
            user_data=key,
            callback=self._on_cell_clicked,
        )
        FontRegistry.bind_to_item(selectable, font)
        dpg.bind_item_theme(selectable, self._subcolumn_themes[subcolumn])
        dpg.bind_item_handler_registry(selectable, self._cell_handler_tag)
        self._editable_cells.register(key, selectable)

    def _update_cursor(self) -> None:
        cursor = self._input_state.cursor
        if cursor is not None:
            if cursor.row < self._current_row_count:
                self._apply_cell_highlight(cursor.row, cursor.generator)
            else:
                self._input_state = TrackerInputState()

        self._update_caret()

    def select_cell(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
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

        self._update_caret()

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

        self._update_caret()

    def update_samples(self, view_model: SequencerSamplesViewModel) -> None:
        self._current_samples = view_model

    def set_enabled(self, enabled: bool) -> None:
        dpg.configure_item(TAG_SEQUENCER_GRID_GROUP_TRACKER, enabled=enabled)

    def _update_cell_display(
        self,
        row: int,
        generator: Optional[GeneratorName],
    ) -> None:
        for subcolumn in SubColumn:
            key = (row, generator, subcolumn)
            cell_id = self._editable_cells.widget(key)
            if cell_id is not None:
                dpg.configure_item(cell_id, label=self._render_cell(key))

    def _update_caret(self) -> None:
        """Arms (or clears) the shared caret box on the active subcolumn cell."""
        cursor = self._input_state.cursor
        if cursor is None:
            CaretOverlay.clear(TAG_SEQUENCER_GRID_TABLE_TRACKER)
            return

        key = (cursor.row, cursor.generator, cursor.subcolumn)
        font = Font.MONO_BOLD_SMALL if cursor.generator is None else Font.MONO_SMALL
        CaretOverlay.set_target(
            owner=TAG_SEQUENCER_GRID_TABLE_TRACKER,
            widget=self._editable_cells.widget(key),
            caret_index=len(self._input_state.pending),
            font=font,
            clip_widget=TAG_SEQUENCER_GRID_WINDOW_TRACKER,
        )

    def _resolve_sample_id(
        self,
        sample_index: int,
    ) -> Optional[Tuple[int, str]]:
        if not self._current_samples or not self._current_samples.samples:
            return None

        samples = self._current_samples.samples
        sample_index = max(0, min(sample_index, len(samples) - 1))
        return sample_index, samples[sample_index].sample_id

    def _handle_edit_action(self, action: EditAction) -> None:
        """Commits a single-subcolumn edit.

        An :class:`EditAction` only ever carries the subcolumn under the cursor;
        the others are ``None`` meaning "leave unchanged". Forwarding those ``None``
        values lets the downstream partial update preserve the rest of the row.
        """
        row, generator = action.row, action.generator

        if action.note_off:
            self._editable_cells.values[(row, generator, SubColumn.INSTRUMENT)] = NOTE_OFF
            self.call(self.on_set_note_off, row, generator)
            return

        sample_id: Optional[str] = None

        if action.sample_index is not None:
            resolved = self._resolve_sample_id(action.sample_index)
            sample_index = resolved[0] if resolved is not None else None
            sample_id = resolved[1] if resolved is not None else None
            self._editable_cells.values[(row, generator, SubColumn.INSTRUMENT)] = tracker_display.format_committed(
                SubColumn.INSTRUMENT,
                sample_index,
            )

        if action.transpose is not None:
            self._editable_cells.values[(row, generator, SubColumn.TRANSPOSE)] = tracker_display.format_committed(
                SubColumn.TRANSPOSE,
                action.transpose,
            )

        if action.volume is not None:
            self._editable_cells.values[(row, generator, SubColumn.VOLUME)] = tracker_display.format_committed(
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
        if action.subcolumn is None:
            for subcolumn in SubColumn:
                self._editable_cells.values.pop(
                    (action.row, action.generator, subcolumn),
                    None,
                )
            self.call(self.on_clear_row, action.row, action.generator)
        else:
            self._editable_cells.values.pop(
                (action.row, action.generator, action.subcolumn),
                None,
            )
            self.call(
                self.on_clear_subcolumn,
                action.row,
                action.generator,
                action.subcolumn,
            )

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
        column_index = tracker_table_column(generator)
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
        col_idx = tracker_table_column(generator)
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
        self._committed_state()
        row_index, generator, subcolumn = user_data
        new_state = TrackerInputState(
            cursor=TrackerCursor(row_index, generator, subcolumn),
            pending="",
        )
        self._apply_state(new_state)

    def _on_cell_right_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
    ) -> None:
        """Opens the cell-operations menu for the right-clicked subcolumn.

        The menu targets the clicked cell directly and leaves the edit cursor where it is,
        so a right-click inspects a cell while the caret stays put.
        """
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        key = dpg.get_item_user_data(clicked_item)
        if key is None:
            return

        row_index, generator, subcolumn = key
        self._show_context_menu(row_index, generator, subcolumn)

    def _show_context_menu(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        subcolumn: SubColumn,
    ) -> None:
        with context_menu():
            header = dpg.add_text(tracker_display.indexed_label(row_index, self._column_labels[generator]))
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            add_play_menu_item(
                self._lbl_context_play,
                lambda: self.call(self.on_play_from_row, row_index),
                shortcut=self._sc_play_from_here,
            )
            add_play_menu_item(
                self._lbl_context_play_from_frame,
                lambda: self.call(self.on_play_from_frame),
                shortcut=self._sc_play_from_frame,
            )
            dpg.add_separator()
            self._add_instrument_submenu(row_index, generator)
            dpg.add_menu_item(
                label=self._lbl_context_note_off,
                callback=lambda: self.call(self.on_set_note_off, row_index, generator),
            )
            dpg.add_separator()
            self._add_transpose_items(row_index, generator)
            dpg.add_separator()
            self._add_volume_items(row_index, generator)
            dpg.add_separator()
            self._add_clear_items(row_index, generator, subcolumn)

    def _add_instrument_submenu(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        with dpg.menu(label=self._lbl_context_set_instrument):
            samples = self._current_samples.samples if self._current_samples is not None else ()
            if not samples:
                dpg.add_menu_item(
                    label=self._lbl_context_no_samples,
                    enabled=False,
                )
                return

            for index, sample in enumerate(samples):
                dpg.add_menu_item(
                    label=tracker_display.indexed_label(index, sample.name),
                    user_data=(row_index, generator, sample.sample_id),
                    callback=self._on_set_instrument_menu,
                )

    def _add_transpose_items(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        for label, delta in (
            (self._lbl_context_transpose_up, SEMITONE_STEP),
            (self._lbl_context_transpose_down, -SEMITONE_STEP),
            (self._lbl_context_transpose_octave_up, OCTAVE_SEMITONES),
            (self._lbl_context_transpose_octave_down, -OCTAVE_SEMITONES),
        ):
            dpg.add_menu_item(
                label=label,
                user_data=(row_index, generator, delta),
                callback=self._on_transpose_menu,
            )

    def _add_volume_items(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        for label, delta in (
            (self._lbl_context_volume_up, VOLUME_FINE_STEP),
            (self._lbl_context_volume_down, -VOLUME_FINE_STEP),
            (self._lbl_context_volume_up_coarse, VOLUME_COARSE_STEP),
            (self._lbl_context_volume_down_coarse, -VOLUME_COARSE_STEP),
        ):
            dpg.add_menu_item(
                label=label,
                user_data=(row_index, generator, delta),
                callback=self._on_volume_menu,
            )

    def _on_set_instrument_menu(
        self,
        sender: Sender,
        app_data: None,
        user_data: Tuple[int, Optional[GeneratorName], str],
    ) -> None:
        row_index, generator, sample_id = user_data
        self.call(self.on_set_row, row_index, generator, sample_id, None, None)

    def _on_transpose_menu(
        self,
        sender: Sender,
        app_data: None,
        user_data: Tuple[int, Optional[GeneratorName], int],
    ) -> None:
        row_index, generator, delta = user_data
        self.call(self.on_adjust_transpose, row_index, generator, delta)

    def _on_volume_menu(
        self,
        sender: Sender,
        app_data: None,
        user_data: Tuple[int, Optional[GeneratorName], int],
    ) -> None:
        row_index, generator, delta = user_data
        self.call(self.on_adjust_volume, row_index, generator, delta)

    def _add_clear_items(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
        subcolumn: SubColumn,
    ) -> None:
        """Builds the three clear levels: the clicked subcolumn, the whole channel cell, the whole row.

        The cell and row levels coincide on the sample column, which already clears every channel,
        so the per-channel ``Clear cell`` item is offered only for an actual channel.
        """
        dpg.add_menu_item(
            label=self._lbl_context_clear_subcolumn,
            callback=lambda: self.call(
                self.on_clear_subcolumn,
                row_index,
                generator,
                subcolumn,
            ),
        )
        if generator is not None:
            dpg.add_menu_item(
                label=self._lbl_context_clear_cell,
                callback=lambda: self.call(
                    self.on_clear_row,
                    row_index,
                    generator,
                ),
            )
        dpg.add_menu_item(
            label=self._lbl_context_clear_row,
            callback=lambda: self.call(self.on_clear_row, row_index, None),
        )

    def _keys_active(self) -> bool:
        """Whether the grid owns the next key: its cursor is set and no field holds the keyboard.

        A focused field keeps the keyboard, so the grid stands down while the user types into an
        input. A modal dialog claims keys at a higher priority in the router, so the grid carries no
        modal check of its own.
        """
        return self._input_state.cursor is not None and not self._router.is_field_focused

    def _on_key_pressed(self, event: KeyEvent) -> bool:
        """Applies a tracker key to the active cell, reporting whether the grid consumed it.

        A modifier-carrying press belongs to the application's global shortcuts, so the grid
        yields it to the lower-priority scopes and keeps the plain keys for tracker editing.
        Ctrl+Shift+Space is the exception: it plays the song from the cursor's row.
        """
        if event.ctrl and event.shift and event.key == dpg.mvKey_Spacebar:
            cursor = self._input_state.cursor
            if cursor is None:
                return False

            self.call(self.on_play_from_row, cursor.row)
            return True

        if event.ctrl:
            return False

        match event.key:
            case dpg.mvKey_Up:
                self._move_row(-1)
            case dpg.mvKey_Down:
                self._move_row(1)
            case dpg.mvKey_Left:
                self._move_subcolumn(-1)
            case dpg.mvKey_Right:
                self._move_subcolumn(1)
            case dpg.mvKey_Tab:
                self._move_column(-1 if event.shift else 1)
            case dpg.mvKey_Home:
                self._jump_to_row(0)
            case dpg.mvKey_End:
                self._jump_to_row(self._current_row_count - 1)
            case dpg.mvKey_Prior:
                self._move_row(-self._layout.tracker.page_size)
            case dpg.mvKey_Next:
                self._move_row(self._layout.tracker.page_size)
            case dpg.mvKey_Return:
                self._move_row(1)
            case dpg.mvKey_Delete:
                self._clear_row()
                self._move_row(1)
            case dpg.mvKey_Back:
                self._clear_row()
                self._move_row(-1)
            case dpg.mvKey_Escape:
                if not self._input_state.pending:
                    return False

                self._apply_state(self._input_state.cancel())
            case _:
                return self._handle_printable_key(event.key)

        return True

    def _move_row(self, delta: int) -> None:
        self._apply_state(
            self._committed_state().navigate_row(
                delta,
                self._current_row_count,
            )
        )

    def _jump_to_row(self, index: int) -> None:
        self._apply_state(
            self._committed_state().navigate_row(
                index,
                self._current_row_count,
                absolute=True,
            )
        )

    def _move_subcolumn(self, delta: int) -> None:
        self._apply_state(self._committed_state().navigate_subcolumn(delta))

    def _move_column(self, delta: int) -> None:
        self._apply_state(self._committed_state().navigate_column_by(delta))

    def _clear_row(self) -> None:
        state, clear_action = self._input_state.clear()
        self._handle_clear_action(clear_action)
        self._apply_state(state)

    def _clear_subcolumn(self) -> None:
        state, clear_action = self._input_state.clear_subcolumn()
        self._handle_clear_action(clear_action)
        self._apply_state(state)

    def _committed_state(self) -> TrackerInputState:
        state, edit_action = self._input_state.commit_partial()
        if edit_action is not None:
            self._handle_edit_action(edit_action)

        return state

    def _handle_printable_key(self, key: int) -> bool:
        char = HEX_KEYS.get(key) or SIGN_KEYS.get(key)
        if char is None:
            return False

        new_state, edit_action = self._input_state.type_char(char)
        if edit_action is not None:
            self._handle_edit_action(edit_action)
            new_state = new_state.navigate_row(1, self._current_row_count)

        self._apply_state(new_state)
        return True

    def _on_row_number_clicked(
        self,
        sender: Sender,
        app_data: bool,
        user_data: int,
    ) -> None:
        dpg.set_value(sender, False)
        existing = self._input_state.cursor
        generator = existing.generator if existing is not None else None
        subcolumn = existing.subcolumn if existing is not None else SubColumn.INSTRUMENT
        self._apply_state(
            TrackerInputState(
                cursor=TrackerCursor(
                    user_data,
                    generator,
                    subcolumn,
                ),
                pending="",
            )
        )

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

    def set_playing_row(self, row_index: Optional[int]) -> None:
        if self._playing_row is not None and self._playing_row < self._live_row_count():
            dpg.unhighlight_table_row(TAG_SEQUENCER_GRID_TABLE_TRACKER, self._playing_row)

        self._playing_row = row_index
        self._apply_playing_row_highlight()

    def _apply_playing_row_highlight(self) -> None:
        """Highlights the playing row when its index lies within the live table.

        Position updates arrive on the callback-queue worker thread, so the table may be shorter
        than ``_playing_row`` if the main thread shrank it (a rows-per-pattern change) in between;
        checking the live row count keeps a stale index from reaching DearPyGui.
        """
        if self._playing_row is not None and self._playing_row < self._live_row_count():
            dpg.highlight_table_row(
                TAG_SEQUENCER_GRID_TABLE_TRACKER,
                self._playing_row,
                color=self._layout.colors.playback_row,
            )

    def _live_row_count(self) -> int:
        """The table's current row count, read live from DearPyGui.

        The cached ``_current_row_count`` reflects the last build on this thread; a concurrent
        rebuild on another thread can leave it stale, so row-index-bounded DearPyGui calls read the
        actual children directly.
        """
        if not dpg.does_item_exist(TAG_SEQUENCER_GRID_TABLE_TRACKER):
            return 0

        rows = dpg.get_item_children(TAG_SEQUENCER_GRID_TABLE_TRACKER, slot=1)
        return len(rows) if rows else 0
