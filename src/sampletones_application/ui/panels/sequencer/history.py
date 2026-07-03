from typing import Any, Callable, Optional

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
from sampletones_application.view_model.sequencer.history import HistoryEntryViewModel, HistoryViewModel
from sampletones_shared.types.application import Sender


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
        dpg.delete_item(TAG_SEQUENCER_HISTORY_WINDOW_LIST, children_only=True)
        if view_model.is_empty:
            self._show_empty()
        else:
            self._create_entry_list(view_model)

    def _update_actions(self, view_model: HistoryViewModel) -> None:
        dpg_configure_item(TAG_SEQUENCER_HISTORY_BUTTON_UNDO, enabled=view_model.can_undo)
        dpg_configure_item(TAG_SEQUENCER_HISTORY_BUTTON_REDO, enabled=view_model.can_redo)

    def _show_empty(self) -> None:
        empty = dpg.add_text(self._lbl_empty, parent=TAG_SEQUENCER_HISTORY_WINDOW_LIST)
        FontRegistry.bind_to_item(empty, Font.REGULAR_SMALL)

    def _create_entry_list(self, view_model: HistoryViewModel) -> None:
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
        for entry in reversed(view_model.entries):
            self._create_entry(table, entry)

        ThemeRegistry.get(TAG_SEQUENCER_HISTORY_THEME_LIST).bind_to_item(table)

    def _create_entry(self, table: int, entry: HistoryEntryViewModel) -> None:
        """Renders one entry as a full-width selectable with two-colour text on top.

        A ``span_columns`` selectable backs the whole row, so clicking anywhere
        jumps to that entry and the current entry keeps the native selected
        highlight. The label and its detail render as separate text items in the
        second column, letting the detail carry its own accent colour while the
        non-interactive text passes clicks through to the selectable beneath.
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

            with dpg.group(horizontal=True):
                self._add_entry_text(entry.label, greyed=entry.is_future)
                if entry.detail is not None:
                    detail_color = (
                        self._layout.colors.history_future if entry.is_future else self._layout.colors.history_detail
                    )
                    self._add_entry_text(entry.detail, color=detail_color)

    def _add_entry_text(
        self,
        value: str,
        *,
        greyed: bool = False,
        color: Optional[RGBA] = None,
    ) -> None:
        """Adds a small-font text item, tinting it only when a colour is called for.

        The label reads in the theme's default colour unless the entry is a future
        (redo) state, where it greys out; the detail always carries an explicit
        accent colour supplied by the caller.
        """
        resolved = self._layout.colors.history_future if greyed else color
        text = dpg.add_text(value) if resolved is None else dpg.add_text(value, color=resolved)
        FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_HISTORY_GROUP_ACTIONS, enabled=enabled)

    def _on_undo_clicked(self, sender: Sender, app_data: Any) -> None:
        self.call(self.on_undo)

    def _on_redo_clicked(self, sender: Sender, app_data: Any) -> None:
        self.call(self.on_redo)

    def _on_entry_clicked(self, sender: Sender, app_data: Any, user_data: int) -> None:
        self.call(self.on_jump_to, user_data)
