from typing import Any, Callable, Dict, FrozenSet, Optional, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_CHANNELS,
    SUF_CHECKBOX,
    SUF_GROUP,
    SUF_HANDLER_REGISTRY,
    SUF_LEVEL,
    SUF_PAYLOAD,
    SUF_ROW,
    SUF_STRIP,
    SUF_TABLE,
    SUF_TEXT,
    SUF_TOOLTIP,
    SUF_WELL,
    TAG_GLOBAL_THEME_CHANNEL_MUTED,
    TAG_GLOBAL_THEME_DANGER_BUTTON,
    TAG_GLOBAL_THEME_STEMS_DROP_STRIP,
    TAG_GLOBAL_THEME_STEMS_ROW,
    TAG_GLOBAL_THEME_STEMS_ROW_INERT,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.layout.well import well
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_item,
    dpg_set_value,
)
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback, StringCallback
from sampletones_shared.utils.callbacks import CallbackMixin

RowShape = Tuple[Tuple[str, ...], bool, Tuple[Tuple[str, int, Tuple[str, ...]], ...]]

ChannelsCallback = Callable[[str, FrozenSet[ChannelName]], None]
KeyOffsetCallback = Callable[[str, int], None]
KeyPairCallback = Callable[[str, str], None]


class GUIStemsList(CallbackMixin):
    """The stems of one setup, as a table of rows banded by the levels they pick on.

    Both the converter's gathered recordings and a reconstruction's recorded assignment are the
    same list, so one definition draws them and each owner turns on the affordances it can
    honour: ``draggable`` makes a row itself the thing you drag and opens a drop strip between
    the bands, ``master_checkbox`` gives the row a leading box moving every channel at once,
    and ``removable`` gives it the danger-toned button that takes it out. Rows are keyed by the
    identity their owner reports gestures under, and every column lines up across the bands
    because each table holds one fixed column per channel in play.
    """

    def __init__(
        self,
        *,
        prefix: str,
        layout: StemsListLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        draggable: bool,
        removable: bool,
        master_checkbox: bool,
    ) -> None:
        self._prefix = prefix
        self._layout = layout
        self._language_manager = language_manager
        self._status_bar = status_bar
        self._draggable = draggable
        self._removable = removable
        self._master_checkbox = master_checkbox

        self._level_template = language_manager["global.stems.template.level_caption"]
        self._lbl_remove = language_manager["global.stems.label.remove"]
        self._msg_drag = language_manager["global.stems.message.drag_tooltip"]
        self._msg_inert = language_manager["global.stems.message.inert_tooltip"]
        self._msg_missing = language_manager["global.stems.message.missing_tooltip"]
        self._msg_unoffered = language_manager["global.stems.message.unoffered_tooltip"]

        self._payload = compose_tag(prefix, SUF_PAYLOAD)
        self._well_tag = compose_tag(prefix, SUF_WELL)
        self._body_tag = compose_tag(self._well_tag, SUF_GROUP)
        self._table_tag = compose_tag(prefix, SUF_TABLE)
        self._name_handler_tag = compose_tag(prefix, SUF_TEXT, SUF_HANDLER_REGISTRY)
        self._channel_handler_tag = compose_tag(prefix, SUF_CHANNELS, SUF_HANDLER_REGISTRY)
        self._master_handler_tag = compose_tag(prefix, SUF_CHECKBOX, SUF_HANDLER_REGISTRY)
        self._button_handler_tag = compose_tag(prefix, SUF_BUTTON, SUF_HANDLER_REGISTRY)

        self._rows: Dict[str, StemRowViewModel] = {}
        self._channels_in_play: Tuple[ChannelName, ...] = ()
        self._muted_channels: FrozenSet[ChannelName] = frozenset()
        self._shape: RowShape = ((), False, ())
        self._live = True

        self.on_channels_changed: Optional[ChannelsCallback] = None
        self.on_remove_requested: Optional[StringCallback] = None
        self.on_menu_requested: Optional[StringCallback] = None
        self.on_row_activated: Optional[StringCallback] = None
        self.on_dropped_on_row: Optional[KeyPairCallback] = None
        self.on_dropped_on_level: Optional[KeyOffsetCallback] = None

    @property
    def _handler_tags(self) -> Tuple[str, ...]:
        """The registries the rows bind to, one per widget kind the list draws."""
        return (
            self._name_handler_tag,
            self._channel_handler_tag,
            self._master_handler_tag,
            self._button_handler_tag,
        )

    @property
    def tag(self) -> str:
        """The recessed region the list is drawn in, which is what an owner shows and hides."""
        return self._well_tag

    @property
    def activatable(self) -> bool:
        """The owner answers a click on a row, so the list hands one on rather than absorbing it."""
        return self.on_row_activated is not None

    @property
    def table_tag(self) -> str:
        """The one table every row stands in while the levels are collapsed."""
        return self._table_tag

    def create(self, parent: str, *, show: bool = True) -> None:
        """Build the list's recessed region and the handlers its rows share."""
        self._create_handlers()
        well(
            parent,
            self._well_tag,
            padding=self._layout.well_padding,
            margin=self._layout.well_margin,
            show=show,
        )

    def update_view(self, view_model: StemsListViewModel) -> None:
        self._rows = {row.key: row for row in view_model.rows}
        self._channels_in_play = view_model.channels_in_play
        self._muted_channels = view_model.muted_channels
        self._live = view_model.live
        self._sync_rows(view_model)
        for row in view_model.rows:
            self._render_row(row)

    def row(self, key: str) -> Optional[StemRowViewModel]:
        """The row a gesture named, as the list last rendered it."""
        return self._rows.get(key)

    def _create_handlers(self) -> None:
        """Register one handler registry per row-widget kind.

        A row's widgets carry their key as user data and share a registry with their kind, so
        the hover explanation and the right-click both read the row they landed on rather than
        needing a handler of their own.
        """
        for handler_tag in self._handler_tags:
            dpg_delete_item(handler_tag)

        with dpg.item_handler_registry(tag=self._name_handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_name_clicked)
            dpg.add_item_hover_handler(callback=self._hover_callback(self._name_message))

        with dpg.item_handler_registry(tag=self._channel_handler_tag):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._channel_message))

        with dpg.item_handler_registry(tag=self._master_handler_tag):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._master_message))

        with dpg.item_handler_registry(tag=self._button_handler_tag):
            dpg.add_item_hover_handler(callback=self._hover_callback(self._remove_message))

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

    def _sync_rows(self, view_model: StemsListViewModel) -> None:
        """Rebuild the bands when the recordings, their levels or their boxes change.

        Collapsing the levels draws every recording in one table, which is the shape a list
        takes where the bands are a record of the setup rather than somewhere to drop onto.
        """
        shape = self._row_shape(view_model)
        if shape == self._shape:
            return

        self._shape = shape
        dpg.delete_item(self._body_tag, children_only=True)
        if view_model.collapse_levels:
            self._create_table(self._table_tag, view_model, view_model.rows)
            return

        for level_index in range(view_model.level_count):
            self._create_level_strip(level_index)
            self._create_level_caption(level_index)
            self._create_level_table(level_index, view_model)

        if view_model.level_count:
            self._create_level_strip(view_model.level_count)

    @staticmethod
    def _row_shape(view_model: StemsListViewModel) -> RowShape:
        """What the bands are built from: the columns, the banding, and where each row stands.

        Which channels a row holds is drawn onto the widgets already standing, so a tick keeps
        the bands as they are and the pointer keeps whatever it was over.
        """
        return (
            tuple(str(channel_name) for channel_name in view_model.channels_in_play),
            view_model.collapse_levels,
            tuple(
                (
                    row.key,
                    row.level,
                    tuple(sorted(str(channel_name) for channel_name in row.offered_channels)),
                )
                for row in view_model.rows
            ),
        )

    def _create_level_strip(self, position: int) -> None:
        """The gap a level is broken at: a recording dropped here takes a level of its own.

        The strip reads as the gap it is and lights up only while a payload hovers it, so a
        band separator stays a separator to everything but a drag.
        """
        if not self._draggable:
            return

        strip = dpg.add_button(
            label="",
            tag=self.level_tag(position, SUF_STRIP),
            parent=self._body_tag,
            height=self._layout.level_strip_height,
            user_data=position,
            payload_type=self._payload,
            drop_callback=self._on_dropped_on_level,
        )
        ThemeRegistry.get(TAG_GLOBAL_THEME_STEMS_DROP_STRIP).bind_to_item(strip)

    def _create_level_caption(self, level_index: int) -> None:
        caption = dpg.add_text(
            self._level_template.format(level_index + 1).upper(),
            tag=self.level_tag(level_index, SUF_TEXT),
            parent=self._body_tag,
        )
        FontRegistry.bind_to_item(caption, Font.MONO_SMALL)

    def _create_level_table(self, level_index: int, view_model: StemsListViewModel) -> None:
        self._create_table(
            self.level_tag(level_index, SUF_TABLE),
            view_model,
            [row for row in view_model.rows if row.level == level_index],
        )

    def _create_table(
        self,
        tag: str,
        view_model: StemsListViewModel,
        rows: Sequence[StemRowViewModel],
    ) -> None:
        """One grid of rows: the master box, the name, a column per channel in play, the button."""
        with dpg.table(
            tag=tag,
            parent=self._body_tag,
            header_row=False,
            policy=dpg.mvTable_SizingFixedFit,
            resizable=False,
        ):
            if self._master_checkbox:
                dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.master_column_width)

            dpg.add_table_column(width_stretch=True)
            for _channel_name in view_model.channels_in_play:
                dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.channel_column_width)

            if self._removable:
                dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.remove_button_width)

            for row in rows:
                self._create_row(row, view_model)

    def _create_row(self, row: StemRowViewModel, view_model: StemsListViewModel) -> None:
        with dpg.table_row(tag=self.row_tag(row.key, SUF_GROUP)):
            if self._master_checkbox:
                self._create_master(row)

            self._create_name(row)
            for channel_name in view_model.channels_in_play:
                self._create_channel(row, channel_name)

            if self._removable:
                self._create_remove(row)

    def _create_master(self, row: StemRowViewModel) -> None:
        """The box moving every channel the row offers at once."""
        master = dpg.add_checkbox(
            tag=self.row_tag(row.key, SUF_CHECKBOX),
            default_value=row.takes_part,
            user_data=row.key,
            callback=self._on_master_changed,
        )
        dpg.bind_item_handler_registry(master, self._master_handler_tag)

    def _create_name(self, row: StemRowViewModel) -> None:
        """The row itself: what names the recording, what you drag it by, and what you drop onto."""
        name = dpg.add_selectable(
            label=row.name,
            tag=self.row_tag(row.key, SUF_TEXT),
            user_data=row.key,
            callback=self._on_name_clicked_off,
            payload_type=self._payload,
            drop_callback=self._on_dropped_on_row,
        )
        if self._draggable:
            with dpg.drag_payload(parent=name, drag_data=row.key, payload_type=self._payload):
                dpg.add_text(row.name)

        FontRegistry.bind_to_item(name, Font.REGULAR_SMALL)
        dpg.bind_item_handler_registry(name, self._name_handler_tag)
        show_tooltip(name, self._row_explanation(row), text_tag=self.row_tag(row.key, SUF_TOOLTIP))

    def _create_channel(self, row: StemRowViewModel, channel_name: ChannelName) -> None:
        """The box giving the recording a channel, where the recording holds frames on it.

        A recording holding none on this channel leaves the cell open, so the columns keep
        lining up across the rows while only a reachable choice is drawn.
        """
        if channel_name not in row.offered_channels:
            dpg.add_spacer()
            return

        checkbox_tag = self.channel_tag(row.key, channel_name)
        dpg.add_checkbox(
            label=channel_label(self._language_manager, channel_name),
            tag=checkbox_tag,
            default_value=channel_name in row.channels,
            user_data=(row.key, channel_name),
            callback=self._on_channels_changed,
        )
        dpg.bind_item_handler_registry(checkbox_tag, self._channel_handler_tag)

    def _create_remove(self, row: StemRowViewModel) -> None:
        remove = dpg.add_button(
            label=self._lbl_remove,
            tag=self.row_tag(row.key, SUF_BUTTON),
            width=self._layout.remove_button_width,
            user_data=row.key,
            callback=self._on_remove_requested,
        )
        FontRegistry.bind_to_item(remove, Font.MONO_SMALL)
        ThemeRegistry.get(TAG_GLOBAL_THEME_DANGER_BUTTON).bind_to_item(remove)
        dpg.bind_item_handler_registry(remove, self._button_handler_tag)

    def _render_row(self, row: StemRowViewModel) -> None:
        """Draw what the row currently holds onto the widgets it already stands as.

        A row contributing nothing greys through its theme rather than through ``enabled``, so
        it answers a drag and a right-click as readily as one in play. A box on a channel
        switched off elsewhere takes the muted tone and stays as clickable as any other.
        """
        for channel_name in self._row_boxes(row):
            tag = self.channel_tag(row.key, channel_name)
            dpg_configure_item(tag, enabled=self._live)
            dpg_set_value(tag, channel_name in row.channels)
            ThemeRegistry.get(self._channel_theme(channel_name)).bind_to_item(tag)

        name_tag = self.row_tag(row.key, SUF_TEXT)
        dpg_set_value(name_tag, False)
        dpg_configure_item(name_tag, enabled=self._live)
        dpg_set_value(self.row_tag(row.key, SUF_TOOLTIP), self._row_explanation(row))
        row_theme = TAG_GLOBAL_THEME_STEMS_ROW if row.in_play else TAG_GLOBAL_THEME_STEMS_ROW_INERT
        ThemeRegistry.get(row_theme).bind_to_item(name_tag)
        if self._master_checkbox:
            master_tag = self.row_tag(row.key, SUF_CHECKBOX)
            dpg_configure_item(master_tag, enabled=self._live and row.offers_channels)
            dpg_set_value(master_tag, row.takes_part)

        if self._removable:
            dpg_configure_item(self.row_tag(row.key, SUF_BUTTON), enabled=self._live)

    def _row_boxes(self, row: StemRowViewModel) -> Tuple[ChannelName, ...]:
        """The channels the row actually draws a box for, in the order the columns stand."""
        return tuple(channel_name for channel_name in self._channels_in_play if channel_name in row.offered_channels)

    def _channel_theme(self, channel_name: ChannelName) -> str:
        """The tone a channel's boxes take: its own colour, muted where the channel is off."""
        if channel_name in self._muted_channels:
            return TAG_GLOBAL_THEME_CHANNEL_MUTED

        return CHANNEL_THEME_TAGS[channel_name]

    def _row_explanation(self, row: StemRowViewModel) -> str:
        """What the row's hover states: where the recording is, why it is greyed out where it
        contributes nothing, and how it moves where the list lets it."""
        lines = [str(row.path)]
        if not row.available:
            lines.append(self._msg_missing)
        elif not row.offers_channels:
            lines.append(self._msg_unoffered)
        elif not row.takes_part:
            lines.append(self._msg_inert)

        if self._draggable:
            lines.append(self._msg_drag)

        return "\n".join(lines)

    def _name_message(self, *_args: Any, user_data: str, **_kwargs: Any) -> str:
        row = self._rows.get(user_data)
        if row is None:
            return ""

        if self._draggable:
            return self._language_manager["global.stems.message.status_row_drag"].format(name=row.name)

        if self.activatable:
            return self._language_manager["global.stems.message.status_row_reveal"].format(name=row.name)

        return row.name

    def _channel_message(
        self,
        *_args: Any,
        user_data: Tuple[str, ChannelName],
        **_kwargs: Any,
    ) -> str:
        key, channel_name = user_data
        row = self._rows.get(key)
        if row is None:
            return ""

        channel = channel_label(self._language_manager, channel_name)
        if channel_name in self._muted_channels:
            return self._language_manager["global.stems.message.status_channel_muted"].format(
                channel=channel,
                name=row.name,
            )

        return self._language_manager["global.stems.message.status_channel"].format(
            channel=channel,
            name=row.name,
        )

    def _master_message(self, *_args: Any, user_data: str, **_kwargs: Any) -> str:
        row = self._rows.get(user_data)
        if row is None:
            return ""

        return self._language_manager["global.stems.message.status_master"].format(name=row.name)

    def _remove_message(self, *_args: Any, user_data: str, **_kwargs: Any) -> str:
        row = self._rows.get(user_data)
        if row is None:
            return ""

        return self._language_manager["global.stems.message.status_remove"].format(name=row.name)

    def _on_channels_changed(
        self,
        _sender: Sender,
        _value: bool,
        user_data: Tuple[str, ChannelName],
    ) -> None:
        key, _channel_name = user_data
        row = self._rows.get(key)
        if row is None:
            return

        channels = frozenset(
            channel_name for channel_name in self._row_boxes(row) if dpg.get_value(self.channel_tag(key, channel_name))
        )
        self.call(self.on_channels_changed, key, channels)

    def _on_master_changed(self, _sender: Sender, value: bool, user_data: str) -> None:
        """The master box hands the row every channel it offers, or takes them all away."""
        row = self._rows.get(user_data)
        if row is None:
            return

        channels = frozenset(self._row_boxes(row)) if value else frozenset()
        self.call(self.on_channels_changed, user_data, channels)

    def _on_remove_requested(self, _sender: Sender, _app_data: Any, user_data: str) -> None:
        self.call(self.on_remove_requested, user_data)

    def _on_name_clicked_off(self, sender: Sender, _value: bool, user_data: str) -> None:
        """Let go of a clicked row and hand it on: the list names recordings, it selects none."""
        dpg_set_value(sender, False)
        if self.activatable:
            self.call(self.on_row_activated, user_data)

    def _on_name_clicked(self, _sender: Sender, app_data: Tuple[int, int]) -> None:
        mouse_button, clicked_item = app_data
        if mouse_button != dpg.mvMouseButton_Right:
            return

        key = dpg.get_item_user_data(clicked_item)
        if isinstance(key, str):
            self.call(self.on_menu_requested, key)

    def _on_dropped_on_row(self, sender: Sender, app_data: str) -> None:
        """A recording was dropped on a row, so it joins that row's level at its place."""
        target = dpg.get_item_user_data(sender)
        if isinstance(target, str):
            self.call(self.on_dropped_on_row, app_data, target)

    def _on_dropped_on_level(self, sender: Sender, app_data: str) -> None:
        """A recording was dropped in a gap, so it takes a level of its own there."""
        position = dpg.get_item_user_data(sender)
        if isinstance(position, int):
            self.call(self.on_dropped_on_level, app_data, position)

    def row_tag(self, key: str, suffix: str) -> str:
        """The tag one of a row's widgets carries, which is how anything outside addresses it."""
        return compose_tag(self._prefix, SUF_ROW, key, suffix)

    def level_tag(self, level_index: int, suffix: str) -> str:
        """The tag one of a band's widgets carries: its caption, its table, or the strip above it."""
        return compose_tag(self._prefix, SUF_LEVEL, str(level_index), suffix)

    def channel_tag(self, key: str, channel_name: ChannelName) -> str:
        """The tag the box giving ``key`` a channel carries."""
        return compose_tag(
            self._prefix,
            SUF_ROW,
            key,
            SUF_CHANNELS,
            compose_tag(channel_name, SUF_CHECKBOX),
        )
