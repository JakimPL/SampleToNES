from typing import Any, Callable, FrozenSet, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_CHANNELS,
    SUF_CHECKBOX,
    SUF_TEXT,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.messages import StemsMessages
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.utils.gui.dpg import dpg_delete_item
from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback, StringCallback

ChannelsCallback = Callable[[str, FrozenSet[ChannelName]], None]
ChannelCallback = Callable[[str, ChannelName], None]
KeyOffsetCallback = Callable[[str, int], None]
KeyPairCallback = Callable[[str, str], None]


class StemsGestures:
    """What a reader does to a stems list, read from DearPyGui's events and reported as keys.

    A row's widgets carry their key as user data and share a registry with their kind, so the
    hover explanation and the right-click read the row they landed on rather than needing a
    handler apiece. Every event this class answers arrives as a widget and a payload; what
    leaves it is the row a gesture named and what the reader asked of it.
    """

    def __init__(
        self,
        tags: StemsTags,
        *,
        messages: StemsMessages,
        status_bar: GUIStatusBar,
    ) -> None:
        self._tags = tags
        self._messages = messages
        self._status_bar = status_bar
        self._view = StemsListViewModel.empty()

        self.on_channels_settled: Optional[ChannelsCallback] = None
        self.on_channel_toggled: Optional[ChannelCallback] = None
        self.on_removal_asked: Optional[StringCallback] = None
        self.on_menu_asked: Optional[StringCallback] = None
        self.on_row_activated: Optional[StringCallback] = None
        self.on_dropped_on_row: Optional[KeyPairCallback] = None
        self.on_dropped_on_level: Optional[KeyOffsetCallback] = None

    @property
    def activatable(self) -> bool:
        """The owner answers a click on a row, so the list hands one on rather than absorbing it."""
        return self.on_row_activated is not None

    def reads(self, view_model: StemsListViewModel) -> None:
        """Takes up the view the list is drawing, which is what a gesture is answered against."""
        self._view = view_model

    def create_handlers(self) -> None:
        """Register one handler registry per row-widget kind."""
        for kind in (SUF_TEXT, SUF_CHANNELS, SUF_CHECKBOX, SUF_BUTTON):
            dpg_delete_item(self._tags.handlers(kind))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_TEXT)):
            dpg.add_item_clicked_handler(callback=self._on_name_clicked)
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.name))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_CHANNELS)):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.channel))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_CHECKBOX)):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.master))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_BUTTON)):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.remove))

    def bind(self, item: str, kind: str) -> None:
        """Puts one row widget under the registry answering for its kind."""
        dpg.bind_item_handler_registry(item, self._tags.handlers(kind))

    def on_channel_box(
        self,
        _sender: Sender,
        _value: bool,
        user_data: Tuple[str, ChannelName],
    ) -> None:
        """A box settles one channel on the row it belongs to.

        A recording answers with every box it now holds ticked, which is the whole of what it
        stands on. A folder's box reads three ways, so it reports the channel alone and its owner
        settles every recording below it — one gesture always moving the group somewhere.
        """
        key, channel_name = user_data
        row = self._view.row(key)
        if row is None:
            return

        if row.stands_for_a_folder:
            self._report(self.on_channel_toggled, key, channel_name)
            return

        channels = frozenset(
            offered for offered in self._view.boxes_of(row) if dpg.get_value(self._tags.channel(key, offered))
        )
        self._report(self.on_channels_settled, key, channels)

    def on_master_box(self, _sender: Sender, value: bool, user_data: str) -> None:
        """The master box hands the row every channel it offers, or takes them all away."""
        row = self._view.row(user_data)
        if row is None:
            return

        channels = frozenset(self._view.boxes_of(row)) if value else frozenset()
        self._report(self.on_channels_settled, user_data, channels)

    def on_remove_button(self, _sender: Sender, _app_data: Any, user_data: str) -> None:
        self._report(self.on_removal_asked, user_data)

    def on_name_selected(self, _sender: Sender, _value: bool, user_data: str) -> None:
        """Hand a clicked row on, and let the next view say which row now reads as picked out."""
        if self.activatable:
            self._report(self.on_row_activated, user_data)

    def on_row_drop(self, sender: Sender, app_data: str) -> None:
        """A recording was dropped on a row, so it joins that row's level at its place."""
        target = dpg.get_item_user_data(sender)
        if isinstance(target, str):
            self._report(self.on_dropped_on_row, app_data, target)

    def on_level_drop(self, sender: Sender, app_data: str) -> None:
        """A recording was dropped in a gap, so it takes a level of its own there."""
        position = dpg.get_item_user_data(sender)
        if isinstance(position, int):
            self._report(self.on_dropped_on_level, app_data, position)

    def _on_name_clicked(self, _sender: Sender, app_data: Tuple[int, int]) -> None:
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        key = dpg.get_item_user_data(clicked_item)
        if isinstance(key, str):
            self._report(self.on_menu_asked, key)

    def _hover_callback(self, message_function: MessageCallback) -> Callable[[Sender, int], None]:
        """Route a hovered row widget's explanation to the status bar.

        An item hover handler names the hovered item, whose user data is the row it belongs to,
        so one callback per widget kind explains every row of that kind. The hover is reported a
        frame after it happened, by which time a rebuilt list may have taken the widget away, so
        the callback answers for the widgets still standing.
        """

        def hover_callback(_sender: Sender, app_data: int) -> None:
            if not dpg.does_item_exist(app_data):
                return

            self._status_bar.set(message_function, user_data=dpg.get_item_user_data(app_data))

        return hover_callback

    def _report(self, callback: Optional[Callable[..., None]], *args: Any) -> None:
        """Hands a gesture on where the list has an owner for it, and drops it where it has none."""
        if callback is not None:
            callback(*args)
