from typing import Optional, Protocol

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.sequencer import SequencerOrderElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.elements.context_menu import add_play_menu_item, context_menu
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.panels.sequencer.channels import ChannelSwitch
from sampletones_application.ui.panels.sequencer.display import cell_title
from sampletones_application.ui.panels.sequencer.input.order import OrderCursor
from sampletones_application.ui.panels.sequencer.input.target import OrderTarget
from sampletones_application.ui.panels.sequencer.order.callbacks import (
    OnFrameActionCallback,
    OnMoveCallback,
    OnRemoveCallback,
    OrderEditSurface,
)
from sampletones_application.ui.panels.sequencer.order.moves import MOVE_DIRECTIONS
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.sequencer.channels import SequencerChannelsViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.utils.callbacks import CallbackMixin


class OrderMenuHost(Protocol):
    """What the order panel states to the menus raised over its table.

    The hooks are the panel's own, so the coordinator keeps wiring them where it already does, and
    a menu reads whichever answer stands at the moment it opens.
    """

    on_play_from_requested: Optional[OnFrameActionCallback]
    on_duplicate_requested: Optional[OnFrameActionCallback]
    on_clone_requested: Optional[OnFrameActionCallback]
    on_insert_requested: Optional[OnFrameActionCallback]
    on_clear_requested: Optional[OnFrameActionCallback]
    on_remove_requested: Optional[OnRemoveCallback]
    on_move_requested: Optional[OnMoveCallback]

    @property
    def edit_surface(self) -> OrderEditSurface: ...

    @property
    def channel_switch(self) -> ChannelSwitch: ...

    @property
    def channels(self) -> Optional[SequencerChannelsViewModel]: ...

    @property
    def position_count(self) -> int: ...

    def row_label(self, channel: Optional[ChannelName]) -> str: ...

    def select_shape(self, shortcut_id: ShortcutId, cell: OrderCursor) -> bool: ...


class OrderMenu(CallbackMixin):
    """Every menu the order table offers, wherever a reader raised it.

    A cell menu names the frame a pointer landed on and a row-label menu the channel beneath it,
    while the menu bar's **Edit** group asks for the cell the cursor stands on. The table states
    its actions once in :meth:`add_action_items`, so an action added there reaches every door.

    What a menu offers about a frame is asked for as it opens — how far it can move, which channels
    stand silenced — which keeps what a menu prints and what a click does one answer.
    """

    def __init__(
        self,
        panel: OrderMenuHost,
        *,
        language_manager: LanguageManager,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._panel = panel
        self._shortcuts = shortcut_source
        self._lbl_play = self._label(language_manager, SequencerOrderElements.CONTEXT_PLAY)
        self._lbl_select_all = self._label(language_manager, SequencerOrderElements.CONTEXT_SELECT_ALL)
        self._lbl_select_row = self._label(language_manager, SequencerOrderElements.CONTEXT_SELECT_ROW)
        self._lbl_duplicate = self._label(language_manager, SequencerOrderElements.CONTEXT_DUPLICATE)
        self._lbl_clone = self._label(language_manager, SequencerOrderElements.CONTEXT_CLONE)
        self._lbl_insert = self._label(language_manager, SequencerOrderElements.CONTEXT_INSERT)
        self._lbl_clear = self._label(language_manager, SequencerOrderElements.CONTEXT_CLEAR)
        self._lbl_remove = self._label(language_manager, SequencerOrderElements.CONTEXT_REMOVE)
        self._lbl_move_left = self._label(language_manager, SequencerOrderElements.CONTEXT_MOVE_LEFT)
        self._lbl_move_right = self._label(language_manager, SequencerOrderElements.CONTEXT_MOVE_RIGHT)
        self._lbl_move_start = self._label(language_manager, SequencerOrderElements.CONTEXT_MOVE_START)
        self._lbl_move_end = self._label(language_manager, SequencerOrderElements.CONTEXT_MOVE_END)

    @staticmethod
    def _label(
        language_manager: LanguageManager,
        element: SequencerOrderElements,
    ) -> str:
        return language_manager[
            Page.SEQUENCER,
            Panel.ORDER,
            TextType.LABEL,
            element,
        ]

    def show_for_channel(self, channel: Optional[ChannelName]) -> None:
        """Opens the menu behind a row label, titled with the row's own name."""
        with context_menu():
            header = dpg.add_text(self._panel.row_label(channel))
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            self._panel.channel_switch.add_menu_items(channel, self._panel.channels)

    def show_for_cell(
        self,
        channel: Optional[ChannelName],
        position: int,
    ) -> None:
        """Opens the frame-operations menu, titled with the cell the pointer landed on."""
        target = self._panel.edit_surface.target_at(OrderCursor(channel, position))
        with context_menu():
            header = dpg.add_text(cell_title(position, self._panel.row_label(channel)))
            FontRegistry.bind_to_item(header, Font.MONO_BOLD)
            dpg.add_separator()
            add_play_menu_item(
                self._lbl_play,
                lambda: self.call(self._panel.on_play_from_requested, position),
                shortcut=self._shortcuts.display(ShortcutId.PLAY_FROM_FRAME),
            )
            dpg.add_separator()
            self.add_action_items(target)

    def add_action_items(self, target: OrderTarget) -> None:
        """Builds every action an order cell offers, in the order each menu prints them.

        The table states its actions once, and whoever asks for them decides where they are shown:
        the cell menu asks for the cell a pointer landed on, and the menu bar asks for the cell the
        cursor stands on. An action added here reaches both.
        """
        self._add_select_items(target.cell)
        dpg.add_separator()
        self._panel.edit_surface.add_block_items(target)
        dpg.add_separator()
        self._add_frame_items(target.cell.position)
        dpg.add_separator()
        self._add_move_items(target.cell.position)

    def _add_select_items(self, cell: OrderCursor) -> None:
        """Builds the two shapes a selection takes, the whole order and one row of it.

        Each item fires the gesture its key fires, on the cell the menu names: a row selected from
        a cell menu is the row that cell stands in, and one selected from the menu bar is the row
        the cursor stands in.
        """
        dpg.add_menu_item(
            label=self._lbl_select_all,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_SELECT_ALL),
            callback=lambda: self._panel.select_shape(ShortcutId.ORDER_SELECT_ALL, cell),
        )
        dpg.add_menu_item(
            label=self._lbl_select_row,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_SELECT_ROW),
            callback=lambda: self._panel.select_shape(ShortcutId.ORDER_SELECT_ROW, cell),
        )

    def _add_frame_items(self, position: int) -> None:
        """Builds the frame operations, each acting on the whole frame the target cell sits in.

        Each item reads its hook as it fires rather than as it is built, so an item answers
        whatever the coordinator has wired by the time a reader clicks it.
        """
        dpg.add_menu_item(
            label=self._lbl_duplicate,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_DUPLICATE_FRAME),
            callback=lambda: self.call(self._panel.on_duplicate_requested, position),
        )
        dpg.add_menu_item(
            label=self._lbl_clone,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_CLONE_FRAME),
            callback=lambda: self.call(self._panel.on_clone_requested, position),
        )
        dpg.add_menu_item(
            label=self._lbl_insert,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_INSERT_FRAME),
            callback=lambda: self.call(self._panel.on_insert_requested, position),
        )
        dpg.add_menu_item(
            label=self._lbl_clear,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_CLEAR_FRAME),
            callback=lambda: self.call(self._panel.on_clear_requested, position),
        )
        dpg.add_menu_item(
            label=self._lbl_remove,
            shortcut=self._shortcuts.display(ShortcutId.ORDER_REMOVE_FRAME),
            callback=lambda: self.call(self._panel.on_remove_requested, position),
        )

    def _add_move_items(self, position: int) -> None:
        """Builds the four moves a frame can make, in the order they walk the song."""
        self._add_move_item(self._lbl_move_left, ShortcutId.ORDER_MOVE_FRAME_LEFT, position)
        self._add_move_item(self._lbl_move_right, ShortcutId.ORDER_MOVE_FRAME_RIGHT, position)
        self._add_move_item(self._lbl_move_start, ShortcutId.ORDER_MOVE_FRAME_TO_START, position)
        self._add_move_item(self._lbl_move_end, ShortcutId.ORDER_MOVE_FRAME_TO_END, position)

    def _add_move_item(
        self,
        label: str,
        shortcut_id: ShortcutId,
        position: int,
    ) -> None:
        """Adds a move item, grayed out (disabled) when the move would have no effect.

        The action names both the direction it moves and the accelerator it prints, so the item a
        reader sees is the one the key press performs.
        """
        target = MOVE_DIRECTIONS[shortcut_id].target(position, self._panel.position_count)
        dpg.add_menu_item(
            label=label,
            shortcut=self._shortcuts.display(shortcut_id),
            enabled=target is not None,
            callback=lambda: self.call(self._panel.on_move_requested, position, target),
        )
