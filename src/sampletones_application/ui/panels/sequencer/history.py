from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerHistoryElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import SUF_PANEL_RIGHT, TAG_GLOBAL_TAB_SEQUENCER
from sampletones_application.constants.sequencer import (
    TAG_SEQUENCER_HISTORY_BUTTON_REDO,
    TAG_SEQUENCER_HISTORY_BUTTON_UNDO,
    TAG_SEQUENCER_HISTORY_GROUP_ACTIONS,
    TAG_SEQUENCER_HISTORY_PANEL,
    TAG_SEQUENCER_HISTORY_THEME_LIST,
    TAG_SEQUENCER_HISTORY_WINDOW_LIST,
)
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.color import RGBA
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.view_model.sequencer.history import (
    HistoryEntryViewModel,
    HistoryViewModel,
)
from sampletones_application.view_model.shared.history import HistoryDetailRole, HistoryDetailSegment
from sampletones_shared.types.application import Sender

EntryWindow = Tuple[HistoryEntryViewModel, ...]
WindowStructure = Tuple[Tuple[int, str, Tuple[HistoryDetailSegment, ...]], ...]


@dataclass
class _EntryRow:
    """The widgets and cursor-relative state of one rendered history row."""

    selectable: int
    group: int
    is_current: bool
    is_future: bool


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
        language_manager: LanguageManager,
    ) -> None:
        self._layout = layout
        self._rows: Dict[int, _EntryRow] = {}
        self._rendered_structure: Optional[WindowStructure] = None

        self.on_undo: Optional[Callable[[], None]] = None
        self.on_redo: Optional[Callable[[], None]] = None
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
        self._lbl_empty = language_manager[
            Page.SEQUENCER,
            Panel.HISTORY,
            TextType.LABEL,
            SequencerHistoryElements.EMPTY,
        ]

        super().__init__(
            tag=TAG_SEQUENCER_HISTORY_PANEL,
            parent=f"{TAG_GLOBAL_TAB_SEQUENCER}{SUF_PANEL_RIGHT}",
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            height=self._layout.history.height,
            border=False,
        ):
            dpg.add_separator()
            header = dpg.add_text(self._lbl_history)
            FontRegistry.bind_to_item(header, Font.BOLD)
            self._create_actions()
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

    def update_view(self, view_model: HistoryViewModel) -> None:
        self._update_actions(view_model)
        window = self._window(view_model)
        structure = self._structure(window)
        if structure == self._rendered_structure:
            self._restyle(window)
            return

        self._rendered_structure = structure
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

    @staticmethod
    def _structure(window: EntryWindow) -> WindowStructure:
        return tuple((entry.index, entry.label, entry.detail_segments) for entry in window)

    def _restyle(self, window: EntryWindow) -> None:
        """Repaints only the rows whose cursor-relative state changed.

        Undo, redo and jumps keep the rendered structure identical — only the
        current marker and the redo-branch dimming move — so stepping through
        history repaints the affected rows in place instead of recreating the
        whole table.
        """
        for entry in window:
            row = self._rows[entry.index]
            if (row.is_current, row.is_future) == (entry.is_current, entry.is_future):
                continue

            row.is_current = entry.is_current
            row.is_future = entry.is_future
            dpg.set_value(row.selectable, entry.is_current)
            dpg.delete_item(row.group, children_only=True)
            self._fill_entry_texts(row.group, entry)

    def _rebuild(self, window: EntryWindow) -> None:
        self._rows = {}
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
        dpg.add_table_column(
            parent=table,
            init_width_or_weight=self._layout.history.selectable_column_weight,
        )
        dpg.add_table_column(parent=table)
        for entry in reversed(window):
            self._create_entry(table, entry)

        ThemeRegistry.get(TAG_SEQUENCER_HISTORY_THEME_LIST).bind_to_item(table)

    def _create_entry(self, table: int, entry: HistoryEntryViewModel) -> None:
        """Renders one entry as a full-width selectable with coloured text on top.

        A ``span_columns`` selectable backs the whole row, so clicking anywhere
        jumps to that entry and the current entry keeps the native selected
        highlight. The label and each detail segment render as separate text items
        in the second column, letting every segment carry its role's colour while
        the non-interactive text passes clicks through to the selectable beneath.
        A future (redo) entry greys every token.
        """
        with dpg.table_row(parent=table):
            selectable = dpg.add_selectable(
                label="",
                span_columns=True,
                default_value=entry.is_current,
                user_data=entry.index,
                callback=self._on_entry_clicked,
            )
            FontRegistry.bind_to_item(selectable, Font.REGULAR_SMALL)
            group = dpg.add_group(horizontal=True)

        self._fill_entry_texts(group, entry)
        self._rows[entry.index] = _EntryRow(
            selectable=selectable,
            group=group,
            is_current=entry.is_current,
            is_future=entry.is_future,
        )

    def _fill_entry_texts(self, group: int, entry: HistoryEntryViewModel) -> None:
        self._add_text(
            entry.label,
            parent=group,
            color=self._layout.colors.history_future if entry.is_future else None,
        )
        for segment in entry.detail_segments:
            color = self._layout.colors.history_future if entry.is_future else self._role_color(segment.role)
            self._add_text(segment.text, parent=group, color=color)

    def _add_text(self, value: str, *, parent: int, color: Optional[RGBA]) -> None:
        text = dpg.add_text(value, parent=parent) if color is None else dpg.add_text(value, parent=parent, color=color)
        FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)

    def _role_color(self, role: HistoryDetailRole) -> RGBA:
        colors = self._layout.colors
        roles = colors.history_roles
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
            case HistoryDetailRole.SAMPLE | HistoryDetailRole.NAME | HistoryDetailRole.FEATURE:
                return text.sample
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
