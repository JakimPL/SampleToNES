from typing import Callable, Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import (
    SequencerTrackerElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HANDLER_HEADER,
    SUF_HANDLER_REGISTRY,
)
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_THEME_TABLE_PATTERN,
    TAG_SEQUENCER_TRACKER_GROUP,
    TAG_SEQUENCER_TRACKER_PANEL,
    TAG_SEQUENCER_TRACKER_TABLE,
    TAG_SEQUENCER_TRACKER_WINDOW,
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
from sampletones_application.ui.panels.sequencer.channels import (
    ChannelMenuLabels,
    ChannelSwitch,
    channel_tooltip,
)
from sampletones_application.ui.panels.sequencer.columns import (
    DIVIDER_TABLE_COLUMN,
    HEADER_TABLE_ROW,
    HEADER_TABLE_ROWS,
    SAMPLE_TABLE_COLUMN,
    TRACKER_TABLE_COLUMNS,
    channel_color,
    tracker_table_column,
    tracker_table_row,
)
from sampletones_application.ui.panels.sequencer.display import CellKey, CellValues
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.edit import (
    ClearAction,
    EditAction,
)
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.rows import RowCues, row_background
from sampletones_application.ui.themes.inline import (
    create_header_selectable_theme,
    create_selectable_text_theme,
)
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_delete_children
from sampletones_application.utils.gui.keyboard import (
    PRIORITY_PANEL,
    ActivePredicate,
    KeyEvent,
    KeyRouter,
)
from sampletones_application.utils.gui.keyboard.keys import HEX_KEYS, SIGN_KEYS
from sampletones_application.utils.gui.keyboard.modifiers import Modifier
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.faded import FadedColor
from sampletones_application.utils.palette.colors.layered import LayeredColor
from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_application.view_model.sequencer.samples import (
    SequencerSamplesViewModel,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import (
    SequencerRowViewModel,
    SequencerTrackerViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.utils.display import NOTE_OFF, display_id
from sampletones_shared.constants.music import OCTAVE_SEMITONES, SEMITONE_STEP
from sampletones_shared.types.application import ColorRGBA, Sender
from sampletones_shared.types.callback import VoidCallback

OnClearRowCallback = Callable[[int, Optional[GeneratorName]], None]
OnClearSubcolumnCallback = Callable[[int, Optional[GeneratorName], SubColumn], None]
OnSetRowCallback = Callable[[int, Optional[GeneratorName], Optional[str], Optional[int], Optional[int]], None]
OnSetNoteOffCallback = Callable[[int, Optional[GeneratorName]], None]
OnCellSelectedCallback = VoidCallback
OnPlayFromRowCallback = Callable[[int], None]
OnPlayFromFrameCallback = VoidCallback
OnAdjustCallback = Callable[[int, Optional[GeneratorName], int], None]
OnChannelMuteToggledCallback = Callable[[GeneratorName], None]
OnChannelSoloedCallback = Callable[[GeneratorName], None]


VOLUME_FINE_STEP: Final[int] = 1
VOLUME_COARSE_STEP: Final[int] = (MAX_VOLUME + 1) // 4


class GUISequencerTrackerPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: SequencerLayout,
        language_manager: LanguageManager,
        key_router: KeyRouter,
        tab_active: ActivePredicate,
        shortcut_source: ShortcutSource,
        initial_collapsed: bool = False,
    ) -> None:
        self._layout = layout
        self._language_manager = language_manager
        self._router = key_router
        self._tab_active = tab_active
        self._shortcuts = shortcut_source

        widths = layout.tracker.subcolumn_widths
        self._subcolumn_widths: Dict[SubColumn, int] = {
            SubColumn.INSTRUMENT: widths.instrument,
            SubColumn.TRANSPOSE: widths.transpose,
            SubColumn.VOLUME: widths.volume,
        }

        self._item_handler_tag = compose_tag(TAG_SEQUENCER_TRACKER_PANEL, SUF_HANDLER_REGISTRY)
        self._cell_handler_tag = compose_tag(TAG_SEQUENCER_TRACKER_TABLE, SUF_HANDLER_REGISTRY)
        self._header_handler_tag = compose_tag(TAG_SEQUENCER_TRACKER_TABLE, SUF_HANDLER_HEADER)

        self._rows: Dict[Optional[int], Sender] = {}
        self._header_columns: Dict[Sender, Optional[GeneratorName]] = {}
        self._editable_cells: EditableCells[CellKey] = EditableCells()
        self._current_row_count: int = 0
        self._highlighted_row: Optional[int] = None
        self._playing_row: Optional[int] = None
        self._input_state: TrackerInputState = TrackerInputState()
        self._subcolumn_themes: Dict[SubColumn, int] = {}
        self._muted_subcolumn_themes: Dict[SubColumn, int] = {}
        self._row_number_theme: int = 0
        self._header_theme: int = 0
        self._muted_header_theme: int = 0
        self._current_samples: Optional[SequencerSamplesViewModel] = None
        self._current_channels: Optional[SequencerChannelsViewModel] = None

        self.on_clear_row: Optional[OnClearRowCallback] = None
        self.on_clear_subcolumn: Optional[OnClearSubcolumnCallback] = None
        self.on_set_row: Optional[OnSetRowCallback] = None
        self.on_set_note_off: Optional[OnSetNoteOffCallback] = None
        self.on_cell_selected: Optional[OnCellSelectedCallback] = None
        self.on_play_from_row: Optional[OnPlayFromRowCallback] = None
        self.on_play_from_frame: Optional[OnPlayFromFrameCallback] = None
        self.on_adjust_transpose: Optional[OnAdjustCallback] = None
        self.on_adjust_volume: Optional[OnAdjustCallback] = None
        self.on_channel_mute_toggled: Optional[OnChannelMuteToggledCallback] = None
        self.on_channel_soloed: Optional[OnChannelSoloedCallback] = None
        self.on_channels_toggled: Optional[VoidCallback] = None
        self.on_channels_muted: Optional[VoidCallback] = None
        self.on_channels_unmuted: Optional[VoidCallback] = None

        self.pattern_theme = ThemeRegistry.get(TAG_SEQUENCER_THEME_TABLE_PATTERN)

        self._lbl_tracker = self._label(
            language_manager,
            SequencerTrackerElements.TRACKER_TEXT,
        )
        self._load_column_labels(language_manager)
        self._load_context_labels(language_manager)
        self._load_header_tooltips(language_manager)
        self._create_channel_switch(language_manager)

        super().__init__(
            tag=TAG_SEQUENCER_TRACKER_PANEL,
            height=-1,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def _load_column_labels(self, language_manager: LanguageManager) -> None:
        """Reads the name each column carries, which its header label and its menu title show."""
        self._lbl_col_row = self._label(language_manager, SequencerTrackerElements.COLUMN_ROW)
        self._column_labels: Dict[Optional[GeneratorName], str] = {
            None: self._label(language_manager, SequencerTrackerElements.COLUMN_SAMPLE),
            GeneratorName.PULSE1: self._label(language_manager, SequencerTrackerElements.COLUMN_PULSE_1),
            GeneratorName.PULSE2: self._label(language_manager, SequencerTrackerElements.COLUMN_PULSE_2),
            GeneratorName.TRIANGLE: self._label(language_manager, SequencerTrackerElements.COLUMN_TRIANGLE),
            GeneratorName.NOISE: self._label(language_manager, SequencerTrackerElements.COLUMN_NOISE),
        }

    @staticmethod
    def _label(
        language_manager: LanguageManager,
        element: SequencerTrackerElements,
    ) -> str:
        return language_manager[
            Page.SEQUENCER,
            Panel.TRACKER,
            TextType.LABEL,
            element,
        ]

    def _load_context_labels(self, language_manager: LanguageManager) -> None:
        def label(element: SequencerTrackerElements) -> str:
            return self._label(language_manager, element)

        self._lbl_context_play = label(SequencerTrackerElements.CONTEXT_PLAY)
        self._lbl_context_play_from_frame = label(SequencerTrackerElements.CONTEXT_PLAY_FROM_FRAME)
        self._lbl_context_note_off = label(SequencerTrackerElements.CONTEXT_NOTE_OFF)
        self._lbl_context_set_instrument = label(SequencerTrackerElements.CONTEXT_SET_INSTRUMENT)
        self._lbl_context_no_samples = label(SequencerTrackerElements.CONTEXT_NO_SAMPLES)
        self._lbl_context_clear_subcolumn = label(SequencerTrackerElements.CONTEXT_CLEAR_SUBCOLUMN)
        self._lbl_context_clear_cell = label(SequencerTrackerElements.CONTEXT_CLEAR_CELL)
        self._lbl_context_clear_row = label(SequencerTrackerElements.CONTEXT_CLEAR_ROW)
        self._lbl_context_transpose_up = label(SequencerTrackerElements.CONTEXT_TRANSPOSE_UP)
        self._lbl_context_transpose_down = label(SequencerTrackerElements.CONTEXT_TRANSPOSE_DOWN)
        self._lbl_context_transpose_octave_up = label(SequencerTrackerElements.CONTEXT_TRANSPOSE_OCTAVE_UP)
        self._lbl_context_transpose_octave_down = label(SequencerTrackerElements.CONTEXT_TRANSPOSE_OCTAVE_DOWN)
        self._lbl_context_volume_up = label(SequencerTrackerElements.CONTEXT_VOLUME_UP)
        self._lbl_context_volume_down = label(SequencerTrackerElements.CONTEXT_VOLUME_DOWN)
        self._lbl_context_volume_up_coarse = label(SequencerTrackerElements.CONTEXT_VOLUME_UP_COARSE)
        self._lbl_context_volume_down_coarse = label(SequencerTrackerElements.CONTEXT_VOLUME_DOWN_COARSE)

    def _load_header_tooltips(self, language_manager: LanguageManager) -> None:
        """Reads the header tooltips, which name the click gestures the labels carry."""

        def tooltip(element: SequencerTrackerElements) -> str:
            return language_manager[Page.SEQUENCER, Panel.TRACKER, TextType.TOOLTIP, element]

        self._tooltip_header_channel = channel_tooltip(tooltip(SequencerTrackerElements.HEADER_CHANNEL))
        self._tooltip_header_sample = tooltip(SequencerTrackerElements.HEADER_SAMPLE)

    def _create_channel_switch(self, language_manager: LanguageManager) -> None:
        """Builds the switch a column header's click and menu act through.

        The hooks are read at call time, so the switch is built here while they are still unset and
        the coordinator wires them once the panel exists.
        """
        labels = ChannelMenuLabels(
            mute=self._label(language_manager, SequencerTrackerElements.CONTEXT_MUTE),
            unmute=self._label(language_manager, SequencerTrackerElements.CONTEXT_UNMUTE),
            solo=self._label(language_manager, SequencerTrackerElements.CONTEXT_SOLO),
            unsolo=self._label(language_manager, SequencerTrackerElements.CONTEXT_UNSOLO),
            mute_all=self._label(language_manager, SequencerTrackerElements.CONTEXT_MUTE_ALL),
            unmute_all=self._label(language_manager, SequencerTrackerElements.CONTEXT_UNMUTE_ALL),
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
        self._setup_handlers()
        self._create_themes()
        self._create_tracker_view(parent)

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_hover_handler(
                parent=self._item_handler_tag,
                callback=self._on_row_hovered,
            )

        with dpg.item_handler_registry(tag=self._cell_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_cell_right_clicked)

        with dpg.item_handler_registry(tag=self._header_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_header_right_clicked)

        self._router.register(
            self._on_key_pressed,
            priority=PRIORITY_PANEL,
            active=self._keys_active,
        )

    def _create_themes(self) -> None:
        self._create_subcolumn_themes()
        self._create_header_themes()
        self._row_number_theme = create_selectable_text_theme(self._layout.colors.text.row)

    def _create_subcolumn_themes(self) -> None:
        """Builds each subcolumn's text theme in its full and its dimmed colour.

        The dimmed variant keeps the subcolumn's own hue at reduced alpha, so a silenced
        channel's values stay readable and editable while the others are worked on.
        """
        subcolumn_colors = self._layout.colors.text
        theme_colors = {
            SubColumn.INSTRUMENT: subcolumn_colors.instrument,
            SubColumn.TRANSPOSE: subcolumn_colors.transpose,
            SubColumn.VOLUME: subcolumn_colors.volume,
        }
        fraction = self._layout.tracker.muted_text_fraction
        for subcolumn, color in theme_colors.items():
            self._subcolumn_themes[subcolumn] = create_selectable_text_theme(color)
            self._muted_subcolumn_themes[subcolumn] = create_selectable_text_theme(
                FadedColor(
                    color=color,
                    fraction=fraction,
                ),
            )

    def _create_header_themes(self) -> None:
        """Builds the two shades a channel's header label takes: audible and silenced.

        Both carry the header's own hover and press washes, so a label reads as the switch it is
        while its text colour reports whether the channel sounds.
        """
        header = self._layout.colors.header
        self._header_theme = create_header_selectable_theme(
            self._layout.colors.label,
            header.hovered,
            header.active,
        )
        self._muted_header_theme = create_header_selectable_theme(
            self._layout.colors.muted.text,
            header.hovered,
            header.active,
        )

    def _create_tracker_view(self, parent: str) -> None:
        """Builds the tracker card and the empty table its rows are filled into.

        The column labels are carried by a row of widgets (see :meth:`_build_header_row`) that
        ``freeze_rows`` pins at the top, which makes each channel's label a click target for
        muting. ``no_clip`` lets a label wider than its column draw across the boundary the way
        a table header does, so the header keeps the size and position it has always had.

        The pattern stands on one even ground: the tracker's own theme
        (``sequencer.theme.table_pattern``) gives ``TableRowBg`` and ``TableRowBgAlt`` the same
        shade, leaving the row background free to carry the beat and bar grouping that tells a
        tracker's rows apart (see :meth:`_row_background`).
        """
        with self._collapsible_card(
            parent,
            self._lbl_tracker,
            glyph=self._glyphs.headers.tracker,
        ):
            dpg.add_group(tag=TAG_SEQUENCER_TRACKER_GROUP)
            with (
                dpg.child_window(
                    tag=TAG_SEQUENCER_TRACKER_WINDOW,
                    parent=TAG_SEQUENCER_TRACKER_GROUP,
                    border=False,
                    width=0,
                    height=-1,
                ),
                dpg.table(
                    tag=TAG_SEQUENCER_TRACKER_TABLE,
                    width=0,
                    header_row=False,
                    resizable=False,
                    borders_innerH=False,
                    borders_innerV=True,
                    borders_outerH=True,
                    borders_outerV=True,
                    scrollX=False,
                    scrollY=True,
                    freeze_rows=HEADER_TABLE_ROWS,
                    row_background=True,
                    policy=dpg.mvTable_SizingFixedFit,
                ),
            ):
                FontRegistry.bind_to_item(dpg.last_item(), Font.MONO_BOLD)
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.row,
                    no_clip=True,
                )
                dpg.add_table_column(
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.sample,
                    no_clip=True,
                )
                dpg.add_table_column(
                    width_fixed=True,
                    init_width_or_weight=self._layout.table_cells.divider,
                )
                for _ in GeneratorName.items():
                    dpg.add_table_column(
                        width_fixed=True,
                        init_width_or_weight=self._layout.table_cells.generator,
                        no_clip=True,
                    )
                dpg.add_table_column(width_stretch=True)

        self.pattern_theme.bind_to_item(TAG_SEQUENCER_TRACKER_TABLE)

    def update_tracker(self, view_model: SequencerTrackerViewModel) -> None:
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
        view_model: SequencerTrackerViewModel,
        cell_values: CellValues,
    ) -> None:
        dpg_delete_children(TAG_SEQUENCER_TRACKER_TABLE, slot=1)
        self._editable_cells.reset(cell_values)
        self._build_table(view_model)
        self.repaint()

    def repaint(self) -> None:
        """Issues every tint the table holds as its own state.

        DearPyGui keeps a row, column or cell highlight on the table rather than on an item,
        so a colour reaches it only by being pushed again. Gathering the pushes here gives
        the palette one call to make and keeps a rebuilt table and a recoloured one identical.
        """
        if not dpg.does_item_exist(TAG_SEQUENCER_TRACKER_TABLE):
            return

        self._highlight_sample_column()
        self._highlight_header_row()
        self._apply_channel_cues()
        self._apply_row_backgrounds()
        self._update_cursor()

    def _row_background(self, row_index: int) -> Optional[BaseColor]:
        """The colour a pattern row's background carries under the marks standing on it now."""
        cursor = self._input_state.cursor
        return row_background(
            row_index,
            self._layout.tracker,
            self._layout.colors,
            RowCues(
                cursor=cursor.row if cursor is not None else None,
                playing=self._playing_row,
            ),
        )

    def _draw_row(
        self,
        row_index: int,
        color: Optional[BaseColor],
    ) -> None:
        """Gives one pattern row the background colour it resolved to.

        Position updates arrive on the callback-queue worker thread, so the table may be shorter
        than the row asked for if the main thread shrank it (a rows-per-pattern change) in between;
        checking the live row count keeps a stale index from reaching DearPyGui.
        """
        if not 0 <= row_index < self._live_row_count():
            return

        table_row = tracker_table_row(row_index)
        if color is None:
            dpg.unhighlight_table_row(
                TAG_SEQUENCER_TRACKER_TABLE,
                table_row,
            )
        else:
            dpg.highlight_table_row(
                TAG_SEQUENCER_TRACKER_TABLE,
                table_row,
                color=color.rgba,
            )

    def _paint_row(self, row_index: int) -> None:
        """Draws a row in the colour its group and the marks on it resolve to."""
        self._draw_row(row_index, self._row_background(row_index))

    def _paint_hovered_row(self, row_index: int) -> None:
        """Draws a row with the hover shade over the background it already carries."""
        background = self._row_background(row_index)
        highlight = self._layout.colors.pattern_highlight
        self._draw_row(
            row_index,
            highlight if background is None else LayeredColor(base=background, overlay=highlight),
        )

    def _apply_row_backgrounds(self) -> None:
        """Draws every live pattern row, which is how the beat and bar grouping reaches the table."""
        for row_index in range(self._live_row_count()):
            self._paint_row(row_index)

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
            TAG_SEQUENCER_TRACKER_TABLE,
            SAMPLE_TABLE_COLUMN,
            self._layout.colors.sample.column.rgba,
        )
        dpg.highlight_table_column(
            TAG_SEQUENCER_TRACKER_TABLE,
            DIVIDER_TABLE_COLUMN,
            self._layout.colors.sample.divider.rgba,
        )

    def _highlight_header_row(self) -> None:
        """Gives the widget header row the background a table header carries.

        The shade is laid cell by cell so it covers the sample and channel column washes,
        which DearPyGui draws over a row highlight; the header then reads as one band with
        the column tints beginning below it.
        """
        for column in range(TRACKER_TABLE_COLUMNS):
            dpg.highlight_table_cell(
                TAG_SEQUENCER_TRACKER_TABLE,
                HEADER_TABLE_ROW,
                column,
                color=self._layout.colors.header.background.rgba,
            )

    def _tint_channel_columns(self) -> None:
        """Washes each channel's column with a faint tint of its identity colour.

        Reapplied after each rebuild alongside the sample column so the tint survives
        row replacement, giving the tracker the same per-channel identity the order
        table carries in its row labels. A silenced channel trades that identity for a
        neutral dark shade, so its column recedes as a whole.
        """
        for generator in GeneratorName.items():
            dpg.highlight_table_column(
                TAG_SEQUENCER_TRACKER_TABLE,
                tracker_table_column(generator),
                self._channel_column_tint(generator),
            )

    def _channel_column_tint(self, generator: GeneratorName) -> ColorRGBA:
        if self._is_muted(generator):
            return self._layout.colors.muted.background.rgba

        channel = channel_color(self._layout.colors.channels, generator)
        return FadedColor(
            color=channel,
            fraction=self._layout.tracker.channel_column_tint,
        ).rgba

    def _compute_cell_values(
        self,
        view_model: SequencerTrackerViewModel,
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

    def _build_table(self, view_model: SequencerTrackerViewModel) -> None:
        self._rows = {}
        self._current_row_count = len(view_model.rows)
        self._build_header_row()
        for row in view_model.rows:
            self._build_table_row(row)

    def _build_header_row(self) -> None:
        """Builds the header as the table's first row, with each channel label a click target.

        A rebuild replaces every row of the table, so the header is raised here, ahead of the
        pattern rows, and lands on the row ``freeze_rows`` pins in place. The cells are
        positional like a pattern row's, so the labels line up with the columns they name.
        """
        self._header_columns = {}
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_TRACKER_TABLE)
        self._add_empty_cell(row_id)
        self._add_header_label_cell(row_id)
        self._add_header_selectable(row_id, None)
        self._add_empty_cell(row_id)
        for generator in GeneratorName.items():
            self._add_header_selectable(row_id, generator)

    def _add_header_label_cell(self, row_id: Sender) -> None:
        """Places the row-number column's label, which names a column the user reads only."""
        label_cell = dpg.add_table_cell(parent=row_id)
        dpg.add_text(self._lbl_col_row, parent=label_cell)

    def _add_header_selectable(
        self,
        row_id: Sender,
        generator: Optional[GeneratorName],
    ) -> None:
        """Places one clickable column label: a channel's mute target, or the master target.

        The selectable takes its width from its label, which is what lets a label wider than
        its column draw in full, and it carries its channel so the click knows which column
        it landed on. A tooltip names the gestures the label answers to, and the right-click
        registry opens the same actions as a menu.
        """
        header_cell = dpg.add_table_cell(parent=row_id)
        selectable = dpg.add_selectable(
            parent=header_cell,
            label=self._column_labels[generator],
            user_data=generator,
            callback=self._on_header_clicked,
        )
        dpg.bind_item_handler_registry(selectable, self._header_handler_tag)
        show_tooltip(
            selectable,
            self._tooltip_header_sample if generator is None else self._tooltip_header_channel,
        )
        self._header_columns[selectable] = generator

    def _build_table_row(self, row: SequencerRowViewModel) -> None:
        """Builds one tracker row.

        The cells are positional, so the empty divider cell after the sample column
        keeps the channel cells aligned with their (shifted) table columns.
        """
        row_id = dpg.add_table_row(
            parent=TAG_SEQUENCER_TRACKER_TABLE,
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

    def deselect_cell(self) -> None:
        cursor = self._input_state.cursor
        if cursor is not None:
            self._input_state = TrackerInputState()
            self._remove_cell_highlight(cursor.row, cursor.generator)

        self._update_caret()

    def _apply_state(self, new_state: TrackerInputState) -> None:
        old_cursor = self._input_state.cursor
        new_cursor = new_state.cursor

        old_pos = (old_cursor.row, old_cursor.generator) if old_cursor is not None else None
        new_pos = (new_cursor.row, new_cursor.generator) if new_cursor is not None else None

        self._input_state = new_state

        if old_pos != new_pos and old_cursor is not None:
            self._remove_cell_highlight(old_cursor.row, old_cursor.generator)

        if old_cursor is not None:
            self._update_cell_display(old_cursor.row, old_cursor.generator)

        if new_cursor is not None:
            if old_pos != new_pos:
                self._apply_cell_highlight(new_cursor.row, new_cursor.generator)
            self._update_cell_display(new_cursor.row, new_cursor.generator)

        if new_pos != old_pos and new_cursor is not None:
            self.call(self.on_cell_selected)

        self._update_caret()

    def update_samples(self, view_model: SequencerSamplesViewModel) -> None:
        self._current_samples = view_model

    def update_channels(self, view_model: SequencerChannelsViewModel) -> None:
        """Shows which channels the song player silences.

        The model is kept so a rebuilt table takes the cue again, the way the column tints do,
        and so a table still waiting for its rows picks it up once they arrive.
        """
        self._current_channels = view_model
        self._apply_channel_cues()

    def _apply_channel_cues(self) -> None:
        """Marks each silenced channel down its whole column: label, background, and cell text.

        The three cues land together because they read as one: the column recedes as a unit
        while its values stay legible, so the channel is visibly out of the mix and still open
        for editing.
        """
        if not dpg.does_item_exist(TAG_SEQUENCER_TRACKER_TABLE):
            return

        self._tint_channel_columns()
        self._bind_header_themes()
        for generator in GeneratorName.items():
            self._bind_channel_cell_themes(generator)

    def _bind_header_themes(self) -> None:
        for selectable, generator in self._header_columns.items():
            muted = generator is not None and self._is_muted(generator)
            dpg.bind_item_theme(
                selectable,
                self._muted_header_theme if muted else self._header_theme,
            )

    def _bind_channel_cell_themes(self, generator: GeneratorName) -> None:
        themes = self._muted_subcolumn_themes if self._is_muted(generator) else self._subcolumn_themes
        for row_index in range(self._current_row_count):
            for subcolumn in SubColumn:
                cell_id = self._editable_cells.widget((row_index, generator, subcolumn))
                if cell_id is not None:
                    dpg.bind_item_theme(cell_id, themes[subcolumn])

    def _is_muted(self, generator: GeneratorName) -> bool:
        return self._current_channels is not None and self._current_channels.is_muted(generator)

    def set_enabled(self, enabled: bool) -> None:
        dpg.configure_item(TAG_SEQUENCER_TRACKER_GROUP, enabled=enabled)

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
            CaretOverlay.clear(TAG_SEQUENCER_TRACKER_TABLE)
            return

        key = (cursor.row, cursor.generator, cursor.subcolumn)
        font = Font.MONO_BOLD_SMALL if cursor.generator is None else Font.MONO_SMALL
        CaretOverlay.set_target(
            owner=TAG_SEQUENCER_TRACKER_TABLE,
            widget=self._editable_cells.widget(key),
            caret_index=len(self._input_state.pending),
            font=font,
            clip_widget=TAG_SEQUENCER_TRACKER_WINDOW,
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
        """Marks the cursor: its cell on the cell layer, its row through the row background."""
        self._paint_row(row_index)
        dpg.highlight_table_cell(
            TAG_SEQUENCER_TRACKER_TABLE,
            tracker_table_row(row_index),
            tracker_table_column(generator),
            color=self._layout.colors.cell_cursor.rgba,
        )

    def _remove_cell_highlight(
        self,
        row_index: int,
        generator: Optional[GeneratorName],
    ) -> None:
        """Clears the cursor cell and returns its row to the background the row itself carries.

        The input state names the row the cursor stands on, so it is updated before this runs
        and the row resolves to what it looks like once the cursor has left.
        """
        dpg.unhighlight_table_cell(
            TAG_SEQUENCER_TRACKER_TABLE,
            tracker_table_row(row_index),
            tracker_table_column(generator),
        )
        self._paint_row(row_index)

    def _on_cell_clicked(
        self,
        sender: Sender,
        _app_data: bool,
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

    def _on_header_clicked(
        self,
        sender: Sender,
        _app_data: bool,
        user_data: Optional[GeneratorName],
    ) -> None:
        self._channel_switch.click(sender, user_data)

    def _on_header_right_clicked(
        self,
        _sender: Sender,
        app_data: Tuple[int, int],
    ) -> None:
        """Opens the channel menu for the right-clicked column header.

        The registry reaches the header labels alone, so a click on one of them names its column
        through the map the header row filled in; a label replaced by a rebuild is absent from it.
        """
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        if clicked_item not in self._header_columns:
            return

        self._show_header_context_menu(self._header_columns[clicked_item])

    def _show_header_context_menu(
        self,
        generator: Optional[GeneratorName],
    ) -> None:
        """Opens the menu behind a column header, titled with the column's own name."""
        with context_menu():
            header = dpg.add_text(self._column_labels[generator])
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            self._channel_switch.add_menu_items(generator, self._current_channels)

    def _on_cell_right_clicked(
        self,
        _sender: Sender,
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
            header = dpg.add_text(
                tracker_display.indexed_label(row_index, self._column_labels[generator]),
            )
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            add_play_menu_item(
                self._lbl_context_play,
                lambda: self.call(self.on_play_from_row, row_index),
                shortcut=self._shortcuts.display(ShortcutId.TRACKER_PLAY_FROM_ROW),
            )
            add_play_menu_item(
                self._lbl_context_play_from_frame,
                lambda: self.call(self.on_play_from_frame),
                shortcut=self._shortcuts.display(ShortcutId.PLAY_FROM_FRAME),
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
        _sender: Sender,
        _app_data: None,
        user_data: Tuple[int, Optional[GeneratorName], str],
    ) -> None:
        row_index, generator, sample_id = user_data
        self.call(self.on_set_row, row_index, generator, sample_id, None, None)

    def _on_transpose_menu(
        self,
        _sender: Sender,
        _app_data: None,
        user_data: Tuple[int, Optional[GeneratorName], int],
    ) -> None:
        row_index, generator, delta = user_data
        self.call(self.on_adjust_transpose, row_index, generator, delta)

    def _on_volume_menu(
        self,
        _sender: Sender,
        _app_data: None,
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
        """Whether the grid owns the next key: its tab is in front, its cursor is set, and no
        field holds the keyboard.

        The grid keeps its cursor while another tab is worked on, so the tab in front is what
        decides whether a press reaches it. A focused field keeps the keyboard, so the grid stands
        down while the user types into an input. A modal dialog claims keys at a higher priority in
        the router, so the grid carries no modal check of its own.
        """
        return self._tab_active() and self._input_state.cursor is not None and not self._router.is_field_focused

    def _on_key_pressed(self, event: KeyEvent) -> bool:
        """Applies a tracker key to the active cell, reporting whether the grid consumed it.

        The scheme says which press each tracker action answers to; a press the tracker category
        leaves unnamed goes to cell entry, which keeps the note and hex keys and hands the rest to
        the application's global shortcuts.
        """
        cursor = self._input_state.cursor
        if cursor is None:
            return False

        shortcut_id = self._shortcuts.action(ShortcutCategory.TRACKER, event)
        if shortcut_id is None:
            return self._type_character(event)

        if shortcut_id is ShortcutId.TRACKER_PLAY_FROM_ROW:
            self.call(self.on_play_from_row, cursor.row)
            return True

        if self._move_cursor(shortcut_id):
            return True

        return self._edit_row(shortcut_id)

    def _move_cursor(self, shortcut_id: ShortcutId) -> bool:
        """Moves the edit cursor over the grid, reporting whether the action was one of its moves."""
        match shortcut_id:
            case ShortcutId.TRACKER_PREVIOUS_ROW:
                self._move_row(-1)
            case ShortcutId.TRACKER_NEXT_ROW:
                self._move_row(1)
            case ShortcutId.TRACKER_PREVIOUS_SUBCOLUMN:
                self._move_subcolumn(-1)
            case ShortcutId.TRACKER_NEXT_SUBCOLUMN:
                self._move_subcolumn(1)
            case ShortcutId.TRACKER_PREVIOUS_COLUMN:
                self._move_column(-1)
            case ShortcutId.TRACKER_NEXT_COLUMN:
                self._move_column(1)
            case ShortcutId.TRACKER_FIRST_ROW:
                self._jump_to_row(0)
            case ShortcutId.TRACKER_LAST_ROW:
                self._jump_to_row(self._current_row_count - 1)
            case ShortcutId.TRACKER_PAGE_UP:
                self._page(-self._layout.tracker.page_size)
            case ShortcutId.TRACKER_PAGE_DOWN:
                self._page(self._layout.tracker.page_size)
            case _:
                return False

        return True

    def _edit_row(self, shortcut_id: ShortcutId) -> bool:
        """Empties the cell under the cursor or drops a partial entry, reporting whether the action
        was one of the cell edits.

        A cancel with nothing typed leaves the press to the application, so Escape stops playback
        while the grid holds a cursor.
        """
        match shortcut_id:
            case ShortcutId.TRACKER_CLEAR_ROW:
                self._clear_row()
                self._move_row(1)
            case ShortcutId.TRACKER_CLEAR_PREVIOUS_ROW:
                self._clear_row()
                self._move_row(-1)
            case ShortcutId.TRACKER_CANCEL_ENTRY:
                if not self._input_state.pending:
                    return False

                self._apply_state(self._input_state.cancel())
            case _:
                return False

        return True

    def _move_row(self, delta: int) -> None:
        self._apply_state(
            self._committed_state().navigate_row(
                delta,
                self._current_row_count,
            )
        )

    def _page(self, delta: int) -> None:
        """Moves the cursor a page of rows, then scrolls it back into view."""
        self._move_row(delta)
        self._scroll_cursor_into_view()

    def _jump_to_row(self, index: int) -> None:
        self._apply_state(
            self._committed_state().navigate_row(
                index,
                self._current_row_count,
                absolute=True,
            )
        )
        self._scroll_cursor_into_view()

    def _move_subcolumn(self, delta: int) -> None:
        self._apply_state(self._committed_state().navigate_subcolumn(delta))

    def _move_column(self, delta: int) -> None:
        self._apply_state(self._committed_state().navigate_column_by(delta))

    def _scroll_cursor_into_view(self) -> None:
        """Scrolls the tracker so the cursor's row stays on screen after a page or Home/End jump.

        The frame's rows all live in one scrolling table, so a jump wider than the visible band
        moves the cursor past it. The scroll is set from the cursor's position within the frame,
        which keeps the row it lands on in view.
        """
        cursor = self._input_state.cursor
        if cursor is None or self._current_row_count <= 1:
            return

        if not dpg.does_item_exist(TAG_SEQUENCER_TRACKER_TABLE):
            return

        scroll_max = dpg.get_y_scroll_max(TAG_SEQUENCER_TRACKER_TABLE)
        if scroll_max <= 0:
            return

        fraction = cursor.row / (self._current_row_count - 1)
        dpg.set_y_scroll(TAG_SEQUENCER_TRACKER_TABLE, fraction * scroll_max)

    def _clear_row(self) -> None:
        state, clear_action = self._input_state.clear()
        self._handle_clear_action(clear_action)
        self._apply_state(state)

    def _committed_state(self) -> TrackerInputState:
        state, edit_action = self._input_state.commit_partial()
        if edit_action is not None:
            self._handle_edit_action(edit_action)

        return state

    def _type_character(self, event: KeyEvent) -> bool:
        """Types a note, digit or sign into the cell under the cursor, reporting whether the press
        was one.

        A press holding Ctrl or Alt is an application gesture, so cell entry reads the plain keys
        and leaves the rest to the global shortcuts.
        """
        if Modifier.CTRL in event.modifiers or Modifier.ALT in event.modifiers:
            return False

        char = HEX_KEYS.get(event.key) or SIGN_KEYS.get(event.key)
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
        _app_data: bool,
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

    def _on_row_hovered(self, _sender: Sender, app_data: int) -> None:
        if not dpg.does_item_exist(app_data):
            return

        row_index = dpg.get_item_user_data(app_data)
        if row_index is not None:
            self._highlighted_row = row_index

    def highlight_row(self, row_index: Optional[int] = None) -> None:
        """Marks the row the pointer rests on, over the background that row already carries."""
        self.unhighlight_row(self._highlighted_row)
        self._highlighted_row = row_index
        if row_index is None:
            return

        self._paint_hovered_row(row_index)

    def unhighlight_row(self, row_index: Optional[int] = None) -> None:
        """Returns a hovered row to the background its group and the marks on it give it."""
        if row_index is None:
            return

        self._highlighted_row = None
        self._paint_row(row_index)

    def set_playing_row(self, row_index: Optional[int]) -> None:
        """Moves the playhead mark, drawing both the row it left and the row it reached."""
        previous = self._playing_row
        self._playing_row = row_index
        if previous is not None and previous != row_index:
            self._paint_row(previous)

        if row_index is not None:
            self._paint_row(row_index)

    def _live_row_count(self) -> int:
        """The table's current pattern-row count, read live from DearPyGui.

        The cached ``_current_row_count`` reflects the last build on this thread; a concurrent
        rebuild on another thread can leave it stale, so row-index-bounded DearPyGui calls read the
        actual children directly. The count covers the pattern rows that follow the header row,
        so it compares against a pattern row index.
        """
        if not dpg.does_item_exist(TAG_SEQUENCER_TRACKER_TABLE):
            return 0

        rows = dpg.get_item_children(TAG_SEQUENCER_TRACKER_TABLE, slot=1)
        return len(rows) - HEADER_TABLE_ROWS if rows else 0
