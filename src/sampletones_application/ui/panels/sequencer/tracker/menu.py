from typing import Dict, Optional, Protocol, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerTrackerElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.elements.context_menu import add_play_menu_item, context_menu
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.panels.sequencer import display as tracker_display
from sampletones_application.ui.panels.sequencer.channels import ChannelSwitch
from sampletones_application.ui.panels.sequencer.input.target import TrackerTarget
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor
from sampletones_application.ui.panels.sequencer.tracker.adjust import (
    TRANSPOSE_ACTIONS,
    VOLUME_ACTIONS,
    AdjustAction,
    AdjustMenuCallback,
)
from sampletones_application.ui.panels.sequencer.tracker.callbacks import (
    OnAdjustCallback,
    OnClearRowCallback,
    OnClearSubcolumnCallback,
    OnPlayFromFrameCallback,
    OnPlayFromRowCallback,
    OnSetNoteOffCallback,
    OnSetRowCallback,
    TrackerEditSurface,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.sequencer.channels import SequencerChannelsViewModel
from sampletones_application.view_model.sequencer.kind import column_takes
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.voices import VoiceEntryViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.callbacks import CallbackMixin


class TrackerMenuHost(Protocol):
    """What the tracker panel states to the menus raised over its grid.

    The hooks are the panel's own, so the coordinator keeps wiring them where it already does, and
    a menu reads whichever answer stands at the moment it opens.
    """

    on_clear_row: Optional[OnClearRowCallback]
    on_clear_subcolumn: Optional[OnClearSubcolumnCallback]
    on_set_row: Optional[OnSetRowCallback]
    on_set_note_off: Optional[OnSetNoteOffCallback]
    on_play_from_row: Optional[OnPlayFromRowCallback]
    on_play_from_frame: Optional[OnPlayFromFrameCallback]
    on_adjust_transpose: Optional[OnAdjustCallback]
    on_adjust_volume: Optional[OnAdjustCallback]

    @property
    def edit_surface(self) -> TrackerEditSurface: ...

    @property
    def channel_switch(self) -> ChannelSwitch: ...

    @property
    def channels(self) -> Optional[SequencerChannelsViewModel]: ...

    @property
    def voices(self) -> Tuple[VoiceEntryViewModel, ...]: ...

    def column_label(self, channel: Optional[ChannelName]) -> str: ...

    def select_shape(self, shortcut_id: ShortcutId, cell: TrackerCursor) -> bool: ...


class TrackerMenu(CallbackMixin):
    """Every menu the tracker grid offers, wherever a reader raised it.

    A cell menu names the cell a pointer landed on and a header menu the column beneath it, while
    the menu bar's **Edit** group asks for the cell the cursor stands on. The grid states its
    actions once in :meth:`add_action_items`, so an action added there reaches every door.

    What a menu offers about a cell is asked for as it opens — the pool a voice is picked from, the
    columns a block covers — which keeps what a menu prints and what a click does one answer.
    """

    def __init__(
        self,
        panel: TrackerMenuHost,
        *,
        language_manager: LanguageManager,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._panel = panel
        self._shortcuts = shortcut_source
        self._lbl_play = self._label(language_manager, SequencerTrackerElements.CONTEXT_PLAY)
        self._lbl_play_from_frame = self._label(language_manager, SequencerTrackerElements.CONTEXT_PLAY_FROM_FRAME)
        self._lbl_select_all = self._label(language_manager, SequencerTrackerElements.CONTEXT_SELECT_ALL)
        self._lbl_select_column = self._label(language_manager, SequencerTrackerElements.CONTEXT_SELECT_COLUMN)
        self._lbl_select_subcolumn = self._label(language_manager, SequencerTrackerElements.CONTEXT_SELECT_SUBCOLUMN)
        self._lbl_note_off = self._label(language_manager, SequencerTrackerElements.CONTEXT_NOTE_OFF)
        self._lbl_set_voice = self._label(language_manager, SequencerTrackerElements.CONTEXT_SET_VOICE)
        self._lbl_no_voices = self._label(language_manager, SequencerTrackerElements.CONTEXT_NO_VOICES)
        self._lbl_clear_subcolumn = self._label(language_manager, SequencerTrackerElements.CONTEXT_CLEAR_SUBCOLUMN)
        self._lbl_clear_cell = self._label(language_manager, SequencerTrackerElements.CONTEXT_CLEAR_CELL)
        self._lbl_clear_row = self._label(language_manager, SequencerTrackerElements.CONTEXT_CLEAR_ROW)
        self._lbl_adjust: Dict[SequencerTrackerElements, str] = {
            element: self._label(language_manager, element) for element, _, _ in (*TRANSPOSE_ACTIONS, *VOLUME_ACTIONS)
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

    def show_for_header(self, channel: Optional[ChannelName]) -> None:
        """Opens the menu behind a column header, titled with the column's own name."""
        with context_menu():
            header = dpg.add_text(self._panel.column_label(channel))
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            self._panel.channel_switch.add_menu_items(channel, self._panel.channels)

    def show_for_cell(
        self,
        row_index: int,
        channel: Optional[ChannelName],
        subcolumn: SubColumn,
    ) -> None:
        """Opens the cell-operations menu, titled with the cell the pointer landed on."""
        target = self._panel.edit_surface.target_at(TrackerCursor(row_index, channel, subcolumn))
        with context_menu():
            header = dpg.add_text(
                tracker_display.cell_title(row_index, self._panel.column_label(channel)),
            )
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            add_play_menu_item(
                self._lbl_play,
                lambda: self.call(self._panel.on_play_from_row, row_index),
                shortcut=self._shortcuts.display(ShortcutId.TRACKER_PLAY_FROM_ROW),
            )
            add_play_menu_item(
                self._lbl_play_from_frame,
                lambda: self.call(self._panel.on_play_from_frame),
                shortcut=self._shortcuts.display(ShortcutId.PLAY_FROM_FRAME),
            )
            dpg.add_separator()
            self.add_action_items(target)

    def add_action_items(self, target: TrackerTarget) -> None:
        """Builds every action a tracker cell offers, in the order each menu prints them.

        The grid states its actions once, and whoever asks for them decides where they are shown:
        the cell menu asks for the cell a pointer landed on, and the menu bar asks for the cell the
        cursor stands on. An action added here reaches both.
        """
        self._add_select_items(target.cell)
        dpg.add_separator()
        self._panel.edit_surface.add_block_items(target)
        dpg.add_separator()
        self._add_voice_submenu(target.cell)
        dpg.add_menu_item(
            label=self._lbl_note_off,
            callback=lambda: self.call(self._panel.on_set_note_off, target.cell.row, target.cell.channel),
        )
        dpg.add_separator()
        self._add_transpose_items(target)
        dpg.add_separator()
        self._add_volume_items(target)
        dpg.add_separator()
        self._add_clear_items(target.cell)

    def _add_select_items(self, cell: TrackerCursor) -> None:
        """Builds the three shapes a selection takes, from the whole frame down to one subcolumn.

        Each item fires the gesture its key fires, on the cell the menu names: a column selected
        from a cell menu is the column that cell stands in, and one selected from the menu bar is
        the column the cursor stands in.
        """
        dpg.add_menu_item(
            label=self._lbl_select_all,
            shortcut=self._shortcuts.display(ShortcutId.TRACKER_SELECT_ALL),
            callback=lambda: self._panel.select_shape(ShortcutId.TRACKER_SELECT_ALL, cell),
        )
        dpg.add_menu_item(
            label=self._lbl_select_column,
            shortcut=self._shortcuts.display(ShortcutId.TRACKER_SELECT_COLUMN),
            callback=lambda: self._panel.select_shape(ShortcutId.TRACKER_SELECT_COLUMN, cell),
        )
        dpg.add_menu_item(
            label=self._lbl_select_subcolumn,
            shortcut=self._shortcuts.display(ShortcutId.TRACKER_SELECT_SUBCOLUMN),
            callback=lambda: self._panel.select_shape(ShortcutId.TRACKER_SELECT_SUBCOLUMN, cell),
        )

    def _add_voice_submenu(self, cell: TrackerCursor) -> None:
        """Offers the pool to a cell, each voice enabled where that cell's column takes it.

        The whole pool is listed wherever the menu is raised, so a reader sees every voice the
        project holds and where each one goes: a channel column takes any of them, while the
        sample column spreads a voice over the channels it covers and so takes a recording alone.
        A voice the column stands by for is offered unreachable, which says it exists while
        leaving it where it belongs.
        """
        with dpg.menu(label=self._lbl_set_voice):
            voices = self._panel.voices
            if not voices:
                dpg.add_menu_item(
                    label=self._lbl_no_voices,
                    enabled=False,
                )
                return

            for index, voice in enumerate(voices):
                dpg.add_menu_item(
                    label=tracker_display.indexed_label(index, voice.name),
                    user_data=(cell.row, cell.channel, voice.voice_id),
                    callback=self._on_set_voice_menu,
                    enabled=column_takes(cell.channel, voice.kind),
                )

    def _add_transpose_items(self, target: TrackerTarget) -> None:
        self._add_adjust_items(target, TRANSPOSE_ACTIONS, self._on_transpose_menu)

    def _add_volume_items(self, target: TrackerTarget) -> None:
        self._add_adjust_items(target, VOLUME_ACTIONS, self._on_volume_menu)

    def _add_adjust_items(
        self,
        target: TrackerTarget,
        actions: Tuple[AdjustAction, ...],
        callback: AdjustMenuCallback,
    ) -> None:
        """Builds one axis of adjustment items, each shifting the cells its target covers.

        An adjustment acts on whole cells, so it reaches the columns the target's block covers and
        the rows it spans: a nudge with a selection standing moves all of it, and one on a cell
        alone moves that cell. Each item prints the key it answers to, since the action states its
        label, its binding and its step in one entry.
        """
        for element, shortcut_id, delta in actions:
            dpg.add_menu_item(
                label=self._lbl_adjust[element],
                shortcut=self._shortcuts.display(shortcut_id),
                user_data=(target.region, delta),
                callback=callback,
            )

    def _on_set_voice_menu(
        self,
        _sender: Sender,
        _app_data: None,
        user_data: Tuple[int, Optional[ChannelName], str],
    ) -> None:
        row_index, channel, voice_id = user_data
        self.call(self._panel.on_set_row, row_index, channel, voice_id, None, None)

    def _on_transpose_menu(
        self,
        _sender: Sender,
        _app_data: None,
        user_data: Tuple[TrackerRegion, int],
    ) -> None:
        region, delta = user_data
        self.call(self._panel.on_adjust_transpose, region, delta)

    def _on_volume_menu(
        self,
        _sender: Sender,
        _app_data: None,
        user_data: Tuple[TrackerRegion, int],
    ) -> None:
        region, delta = user_data
        self.call(self._panel.on_adjust_volume, region, delta)

    def _add_clear_items(self, cell: TrackerCursor) -> None:
        """Builds the three clear levels: the target's subcolumn, its whole channel cell, its whole row.

        The cell and row levels coincide on the sample column, which already clears every channel,
        so the per-channel ``Clear cell`` item is offered only for an actual channel.
        """
        dpg.add_menu_item(
            label=self._lbl_clear_subcolumn,
            callback=lambda: self.call(
                self._panel.on_clear_subcolumn,
                cell.row,
                cell.channel,
                cell.subcolumn,
            ),
        )
        if cell.channel is not None:
            dpg.add_menu_item(
                label=self._lbl_clear_cell,
                callback=lambda: self.call(
                    self._panel.on_clear_row,
                    cell.row,
                    cell.channel,
                ),
            )
        dpg.add_menu_item(
            label=self._lbl_clear_row,
            callback=lambda: self.call(self._panel.on_clear_row, cell.row, None),
        )
