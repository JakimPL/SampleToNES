from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import (
    SequencerHistoryElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.colors import FeatureColors
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_HISTORY_BUTTON_REDO,
    TAG_SEQUENCER_HISTORY_BUTTON_UNDO,
    TAG_SEQUENCER_HISTORY_GROUP_ACTIONS,
    TAG_SEQUENCER_HISTORY_PANEL,
    TAG_SEQUENCER_HISTORY_THEME_LIST,
    TAG_SEQUENCER_HISTORY_WINDOW_LIST,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.view_model.sequencer.history import (
    HistoryEntryViewModel,
    HistoryViewModel,
)
from sampletones_application.view_model.shared.history import (
    HistoryDetailRole,
    HistoryDetailSegment,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.color import RGBA

EntryWindow = Tuple[HistoryEntryViewModel, ...]

APPEND_TO_TABLE: Final[int] = 0


@dataclass
class _EntryRow:
    """The widgets and rendered state of one history row."""

    row: int
    selectable: int
    group: int
    label: str
    segments: Tuple[HistoryDetailSegment, ...]
    is_current: bool
    is_future: bool

    def matches(self, entry: HistoryEntryViewModel) -> bool:
        return (self.label, self.segments, self.is_current, self.is_future) == (
            entry.label,
            entry.detail_segments,
            entry.is_current,
            entry.is_future,
        )


class GUISequencerHistoryPanel(GUIPanel):
    """Shows the undo/redo stack: labelled entries with the current state marked.

    Selecting an entry jumps the project to that state; the Undo and Redo buttons
    step one entry at a time. Entries past the current one are the redo branch and
    render dimmed until they are reached again.
    """

    def __init__(
        self,
        *,
        layout: SequencerLayout,
        feature_colors: FeatureColors,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        initial_collapsed: bool = False,
    ) -> None:
        self._layout = layout
        self._feature_colors = feature_colors
        self._status_bar = status_bar
        self._rows: Dict[int, _EntryRow] = {}
        self._table: Optional[int] = None

        self.on_undo: Optional[VoidCallback] = None
        self.on_redo: Optional[VoidCallback] = None
        self.on_jump_to: Optional[Callable[[int], None]] = None

        self._lbl_history = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryElements.HISTORY_TEXT,
        ]
        self._lbl_undo = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryElements.UNDO,
        ]
        self._lbl_redo = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryElements.REDO,
        ]
        self._msg_status_undo = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.MESSAGE,
            SequencerHistoryElements.STATUS_UNDO,
        ]
        self._msg_status_redo = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.MESSAGE,
            SequencerHistoryElements.STATUS_REDO,
        ]
        self._lbl_empty = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryElements.EMPTY,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_HISTORY_PANEL,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed, fill=True)

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._lbl_history,
            glyph=self._glyphs.headers.history,
            width=0,
        ):
            self._create_actions()
            self._create_window_list()

    def _create_window_list(self) -> None:
        dpg.add_child_window(
            tag=TAG_SEQUENCER_HISTORY_WINDOW_LIST,
            width=-1,
            height=-1,
            border=True,
        )

    def _create_actions(self) -> None:
        with dpg.group(tag=TAG_SEQUENCER_HISTORY_GROUP_ACTIONS):
            with dpg.table(
                header_row=False,
                policy=dpg.mvTable_SizingStretchSame,
                resizable=False,
                width=-1,
            ):
                dpg.add_table_column()
                dpg.add_table_column()
                with dpg.table_row():
                    GUIButton(
                        tag=TAG_SEQUENCER_HISTORY_BUTTON_UNDO,
                        label=self._lbl_undo,
                        callback=self._on_undo_clicked,
                        width=-1,
                    )
                    GUIButton(
                        tag=TAG_SEQUENCER_HISTORY_BUTTON_REDO,
                        label=self._lbl_redo,
                        callback=self._on_redo_clicked,
                        width=-1,
                    )
        self._status_bar.bind_to_item(TAG_SEQUENCER_HISTORY_BUTTON_UNDO, self._msg_status_undo)
        self._status_bar.bind_to_item(TAG_SEQUENCER_HISTORY_BUTTON_REDO, self._msg_status_redo)

    def update_view(self, view_model: HistoryViewModel) -> None:
        self._update_actions(view_model)
        window = self._window(view_model)
        if window and self._table is not None:
            self._sync(window)
            return

        self._rebuild(window)

    def _update_actions(self, view_model: HistoryViewModel) -> None:
        dpg_configure_item(TAG_SEQUENCER_HISTORY_BUTTON_UNDO, enabled=view_model.can_undo)
        dpg_configure_item(TAG_SEQUENCER_HISTORY_BUTTON_REDO, enabled=view_model.can_redo)

    def _window(self, view_model: HistoryViewModel) -> EntryWindow:
        """Selects the slice of entries rendered around the cursor.

        Rendering is capped at ``max_rendered_entries`` so a full-budget history
        keeps the panel responsive; the window tracks the cursor, keeping the
        current entry visible and clickable. Entries beyond the window are
        reached by stepping the cursor towards them.
        """
        limit = self._layout.history.max_rendered_entries
        entries = view_model.entries
        if len(entries) <= limit:
            return entries

        start = min(max(view_model.cursor - limit // 2, 0), len(entries) - limit)
        return entries[start : start + limit]

    def _sync(self, window: EntryWindow) -> None:
        """Aligns the rendered rows with the window, touching only what changed.

        Rows are keyed by entry index: rows leaving the window are removed, rows
        the window gains are inserted at their display position, and rows whose
        text or cursor-relative state changed are repainted in place. Appends,
        coalesced replacements, window slides, and undo/redo therefore each cost
        a handful of rows rather than a table rebuild.
        """
        desired = {entry.index for entry in window}
        for index in list(self._rows):
            if index not in desired:
                dpg.delete_item(self._rows.pop(index).row)

        for entry in window:
            row = self._rows.get(entry.index)
            if row is None:
                self._insert_row(entry)
            elif not row.matches(entry):
                self._repaint_row(row, entry)

    def _insert_row(self, entry: HistoryEntryViewModel) -> None:
        """Places a new row at the position its index dictates.

        The table displays entries newest-first, so a row belongs directly above
        the rendered row with the closest smaller index; an entry older than
        every rendered one lands at the bottom.
        """
        assert self._table is not None

        older = [index for index in self._rows if index < entry.index]
        before = self._rows[max(older)].row if older else APPEND_TO_TABLE
        self._create_entry(self._table, entry, before=before)

    def _repaint_row(self, row: _EntryRow, entry: HistoryEntryViewModel) -> None:
        row.label = entry.label
        row.segments = entry.detail_segments
        row.is_current = entry.is_current
        row.is_future = entry.is_future
        dpg.set_value(row.selectable, entry.is_current)
        dpg.delete_item(row.group, children_only=True)
        self._fill_entry_texts(row.group, entry)

    def _rebuild(self, window: EntryWindow) -> None:
        self._rows = {}
        self._table = None
        dpg.delete_item(TAG_SEQUENCER_HISTORY_WINDOW_LIST, children_only=True)
        if window:
            self._create_entry_list(window)
        else:
            self._show_empty()

    def _show_empty(self) -> None:
        empty = dpg.add_text(self._lbl_empty, parent=TAG_SEQUENCER_HISTORY_WINDOW_LIST)
        FontRegistry.bind_to_item(empty, Font.REGULAR_SMALL)

    def _create_entry_list(self, window: EntryWindow) -> None:
        table = dpg.add_table(
            parent=TAG_SEQUENCER_HISTORY_WINDOW_LIST,
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            borders_innerH=False,
            borders_outerH=False,
            borders_innerV=False,
            borders_outerV=False,
        )
        self._table = table
        dpg.add_table_column(
            parent=table,
            init_width_or_weight=self._layout.history.selectable_column_weight,
        )
        dpg.add_table_column(parent=table)
        for entry in reversed(window):
            self._create_entry(table, entry, before=APPEND_TO_TABLE)

        ThemeRegistry.get(TAG_SEQUENCER_HISTORY_THEME_LIST).bind_to_item(table)

    def _create_entry(self, table: int, entry: HistoryEntryViewModel, *, before: int) -> None:
        """Renders one entry as a full-width selectable with coloured text on top.

        A ``span_columns`` selectable backs the whole row, so clicking anywhere
        jumps to that entry and the current entry keeps the native selected
        highlight. The label and each detail segment render as separate text items
        in the second column, letting every segment carry its role's colour while
        the non-interactive text passes clicks through to the selectable beneath.
        A future (redo) entry greys every token.
        """
        with dpg.table_row(parent=table, before=before) as row:
            selectable = dpg.add_selectable(
                label="",
                span_columns=True,
                default_value=entry.is_current,
                user_data=entry.index,
                callback=self._on_entry_clicked,
            )
            FontRegistry.bind_to_item(selectable, Font.MONO_SMALL)
            group = dpg.add_group(horizontal=True)

        self._fill_entry_texts(group, entry)
        self._rows[entry.index] = _EntryRow(
            row=row,
            selectable=selectable,
            group=group,
            label=entry.label,
            segments=entry.detail_segments,
            is_current=entry.is_current,
            is_future=entry.is_future,
        )

    def _fill_entry_texts(self, group: int, entry: HistoryEntryViewModel) -> None:
        self._add_text(
            entry.label,
            parent=group,
            color=self._layout.colors.history.future if entry.is_future else None,
        )
        for segment in entry.detail_segments:
            color = self._layout.colors.history.future if entry.is_future else self._role_color(segment.role)
            self._add_text(segment.text, parent=group, color=color)

    def _add_text(self, value: str, *, parent: int, color: Optional[RGBA]) -> None:
        text = dpg.add_text(value, parent=parent) if color is None else dpg.add_text(value, parent=parent, color=color)
        FontRegistry.bind_to_item(text, Font.MONO_SMALL)

    def _role_color(self, role: HistoryDetailRole) -> RGBA:
        colors = self._layout.colors
        roles = colors.history.roles
        text = colors.text
        match role:
            case HistoryDetailRole.FRAME:
                return text.frame
            case HistoryDetailRole.CHANNEL:
                return roles.channel
            case HistoryDetailRole.ROW:
                return text.row
            case HistoryDetailRole.INSTRUMENT:
                return text.instrument
            case HistoryDetailRole.TRANSPOSE:
                return text.transpose
            case HistoryDetailRole.VOLUME:
                return text.volume
            case HistoryDetailRole.VALUE:
                return roles.value
            case HistoryDetailRole.SAMPLE | HistoryDetailRole.NAME:
                return text.sample
            case HistoryDetailRole.FEATURE_VOLUME:
                return self._feature_colors.volume
            case HistoryDetailRole.FEATURE_ARPEGGIO:
                return self._feature_colors.arpeggio
            case HistoryDetailRole.FEATURE_PITCH:
                return self._feature_colors.pitch
            case HistoryDetailRole.FEATURE_DUTY_CYCLE:
                return self._feature_colors.duty_cycle
            case HistoryDetailRole.SEPARATOR:
                return roles.separator

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_HISTORY_GROUP_ACTIONS, enabled=enabled)

    def _on_undo_clicked(self, sender: Sender, app_data: Any) -> None:
        self.call(self.on_undo)

    def _on_redo_clicked(self, sender: Sender, app_data: Any) -> None:
        self.call(self.on_redo)

    def _on_entry_clicked(self, sender: Sender, app_data: Any, user_data: int) -> None:
        self.call(self.on_jump_to, user_data)
