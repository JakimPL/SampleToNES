from typing import Any, Callable, FrozenSet, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_CHANNELS,
    SUF_CHECKBOX,
    SUF_TEXT,
    SUF_TWISTY,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.messages import StemsMessages
from sampletones_application.ui.elements.stems.tags import StemsTags
from sampletones_application.utils.gui.dpg import dpg_delete_item, dpg_set_value
from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback, StringCallback

ChannelsCallback = Callable[[str, FrozenSet[ChannelName]], None]
ChannelCallback = Callable[[str, ChannelName], None]
RowSelectionCallback = Callable[[str, bool], None]
KeyOffsetCallback = Callable[[str, int], None]
KeyPairCallback = Callable[[str, str], None]


class StemsGestures:
    """What a reader does to a stems list, read from DearPyGui's events and reported as keys.

    A row's widgets carry their key as user data and share a registry with their kind, so the
    hover explanation and the right-click read the row they landed on rather than needing a
    handler apiece. Every event this class answers arrives as a widget and a payload; what
    leaves it is the row a gesture named and what the reader asked of it.

    Three of those gestures reach past the row to whoever owns the list — picking a row out,
    sounding it, and putting its menu up — so the list is asked whether it has an owner for each.
    A gesture with none rests here, and the widget it moved is put back where it stood.
    """

    def __init__(
        self,
        tags: StemsTags,
        *,
        messages: StemsMessages,
        status_bar: GUIStatusBar,
        activatable: Callable[[], bool],
        playable: Callable[[], bool],
        has_menu: Callable[[], bool],
    ) -> None:
        self._tags = tags
        self._messages = messages
        self._status_bar = status_bar
        self._activatable = activatable
        self._playable = playable
        self._has_menu = has_menu
        self._view = StemsListViewModel.empty()

        self.on_channels_settled: Optional[ChannelsCallback] = None
        self.on_channel_toggled: Optional[ChannelCallback] = None
        self.on_removal_asked: Optional[StringCallback] = None
        self.on_menu_asked: Optional[StringCallback] = None
        self.on_row_activated: Optional[RowSelectionCallback] = None
        self.on_dropped_on_row: Optional[KeyPairCallback] = None
        self.on_dropped_on_level: Optional[KeyOffsetCallback] = None
        self.on_folder_toggled: Optional[StringCallback] = None
        self.on_row_opened: Optional[StringCallback] = None
        self.on_row_picked: Optional[StringCallback] = None

    def reads(self, view_model: StemsListViewModel) -> None:
        """Takes up the view the list is drawing, which is what a gesture is answered against."""
        self._view = view_model

    def create_handlers(self) -> None:
        """Register one handler registry per row-widget kind."""
        for kind in (SUF_TEXT, SUF_CHANNELS, SUF_CHECKBOX, SUF_BUTTON, SUF_TWISTY):
            dpg_delete_item(self._tags.handlers(kind))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_TEXT)):
            dpg.add_item_clicked_handler(callback=self._on_name_clicked)
            dpg.add_item_double_clicked_handler(callback=self._on_name_double_clicked)
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.name))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_CHANNELS)):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.channel))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_CHECKBOX)):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.master))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_BUTTON)):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.remove))

        with dpg.item_handler_registry(tag=self._tags.handlers(SUF_TWISTY)):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._messages.twisty))

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

    def on_pick_box(self, _sender: Sender, _value: bool, user_data: str) -> None:
        """The box beside a row picks the recordings it stands for, or lets them go."""
        self._report(self.on_row_picked, user_data)

    def on_remove_button(self, _sender: Sender, _app_data: Any, user_data: str) -> None:
        self._report(self.on_removal_asked, user_data)

    def on_twisty(self, _sender: Sender, _app_data: Any, user_data: str) -> None:
        """The marker beside a folder's name puts its recordings in view, or away again."""
        self._report(self.on_folder_toggled, user_data)

    def on_name_selected(self, _sender: Sender, value: bool, user_data: str) -> None:
        """Hand a clicked row on, along with whether it now reads as picked out or as let go.

        A row already picked out reads as let go when it is clicked again, which is the answer
        DearPyGui hands the callback, so one gesture both picks a row and releases it.

        A list whose owner answers no click has the row put back the way the view holds it: the
        click moved the widget and nothing behind it, so the row would otherwise keep a picked
        look that no reading of the list ever wrote.
        """
        if not self._activatable():
            dpg_set_value(self._tags.row(user_data, SUF_TEXT), user_data == self._view.selected_key)
            return

        self._report(self.on_row_activated, user_data, value)

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
        """A right-click names the row its menu stands over, where the owner puts one up."""
        if not self._has_menu():
            return

        key = self._named_by(app_data, dpg.mvMouseButton_Right)
        if key is not None:
            self._report(self.on_menu_asked, key)

    def _on_name_double_clicked(self, _sender: Sender, app_data: Tuple[int, int]) -> None:
        """A double-click opens what it landed on: a folder shows what it holds, a recording sounds."""
        key = self._named_by(app_data, dpg.mvMouseButton_Left)
        if key is None:
            return

        row = self._view.row(key)
        if row is not None and row.stands_for_a_folder:
            self._report(self.on_folder_toggled, key)
            return

        if self._playable():
            self._report(self.on_row_opened, key)

    @staticmethod
    def _named_by(app_data: Tuple[int, int], button: int) -> Optional[str]:
        """The row a mouse gesture landed on, for the button the gesture speaks for."""
        mouse_button, clicked_item = app_data
        if mouse_button != button:
            return None

        key = dpg.get_item_user_data(clicked_item)
        return key if isinstance(key, str) else None

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
