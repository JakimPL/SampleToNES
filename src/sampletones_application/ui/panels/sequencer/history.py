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
    TAG_SEQUENCER_HISTORY_WINDOW_LIST,
)
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
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
        self._future_theme: int = 0

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
        with dpg.theme() as self._future_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, self._layout.colors.history_future)

        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            height=self._layout.history.height,
            border=False,
        ):
            dpg.add_separator()
            header = dpg.add_text(self._lbl_history)
            FontRegistry.bind_to_item(header, Font.BOLD)
            with dpg.group(tag=TAG_SEQUENCER_HISTORY_GROUP_ACTIONS, horizontal=True):
                dpg.add_button(
                    tag=TAG_SEQUENCER_HISTORY_BUTTON_UNDO,
                    label=self._lbl_undo,
                    callback=self._on_undo_clicked,
                )
                dpg.add_button(
                    tag=TAG_SEQUENCER_HISTORY_BUTTON_REDO,
                    label=self._lbl_redo,
                    callback=self._on_redo_clicked,
                )
            dpg.add_child_window(
                tag=TAG_SEQUENCER_HISTORY_WINDOW_LIST,
                width=-1,
                height=-1,
                border=True,
            )

    def update_view(self, view_model: HistoryViewModel) -> None:
        dpg_configure_item(TAG_SEQUENCER_HISTORY_BUTTON_UNDO, enabled=view_model.can_undo)
        dpg_configure_item(TAG_SEQUENCER_HISTORY_BUTTON_REDO, enabled=view_model.can_redo)
        dpg.delete_item(TAG_SEQUENCER_HISTORY_WINDOW_LIST, children_only=True)

        if view_model.is_empty:
            empty = dpg.add_text(self._lbl_empty, parent=TAG_SEQUENCER_HISTORY_WINDOW_LIST)
            FontRegistry.bind_to_item(empty, Font.REGULAR_SMALL)
            return

        for entry in reversed(view_model.entries):
            self._create_entry(entry)

    def _create_entry(self, entry: HistoryEntryViewModel) -> None:
        selectable = dpg.add_selectable(
            label=entry.text,
            default_value=entry.is_current,
            user_data=entry.index,
            callback=self._on_entry_clicked,
            parent=TAG_SEQUENCER_HISTORY_WINDOW_LIST,
        )
        FontRegistry.bind_to_item(selectable, Font.REGULAR_SMALL)
        if entry.is_future:
            dpg.bind_item_theme(selectable, self._future_theme)

    def set_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_HISTORY_GROUP_ACTIONS, enabled=enabled)

    def _on_undo_clicked(self, sender: Sender, app_data: Any) -> None:
        self.call(self.on_undo)

    def _on_redo_clicked(self, sender: Sender, app_data: Any) -> None:
        self.call(self.on_redo)

    def _on_entry_clicked(self, sender: Sender, app_data: Any, user_data: int) -> None:
        self.call(self.on_jump_to, user_data)
