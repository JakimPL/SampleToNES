from typing import Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.sources import SettingsField
from sampletones_application.layout.tabs.main.source import SourceSettingsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_CHECKBOX,
    SUF_HANDLER_REGISTRY,
    SUF_HEADING,
    SUF_SLIDER,
    SUF_TEXT,
    SUF_TOOLTIP,
    TAG_GLOBAL_THEME_CHANNEL_MUTED,
    TAG_GLOBAL_THEME_STEMS_SLOT_LABEL,
)
from sampletones_application.tags.main import PRE_MAIN_SOURCE_CHANNEL, TAG_MAIN_SOURCE_TABLE_CHANNELS
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS, PARTIAL_CHANNEL_THEME_TAGS
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.view_model.main.source import ChannelSettingsViewModel, SourceSettingsPanelViewModel
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.algorithm import MAX_DRIVE, MIN_DRIVE
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.callbacks import CallbackMixin

SlotCallback = Callable[[SettingsField, ChannelName], None]
DriveCallback = Callable[[ChannelName, float], None]


class ChannelSettingsRows(CallbackMixin):
    """The channels a recording is converted on, one line apiece.

    A line names its channel in the channel's color and holds what the recording says about it:
    the box using the channel, the box bending it where the hardware reads a bend, and the slider
    driving it. A line whose channel no inspected recording uses reads muted, and its bend and
    drive take no gesture. A drive is reported once its slider is let go, so a drag is one edit,
    and a slider under the reader's hand keeps the value they are setting whatever the card is
    told meanwhile.
    """

    def __init__(
        self,
        *,
        layout: SourceSettingsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._layout = layout
        self._language_manager = language_manager
        self._status_bar = status_bar
        self._lbl_on = language_manager["global.stems.label.channel_on"]
        self._lbl_bend = language_manager["global.stems.label.channel_bend"]
        self._lbl_drive = language_manager["main.source.label.drive"]
        self._lbl_mixed = language_manager["main.source.label.drive_mixed"]
        self._msg_bend = language_manager["global.stems.message.bend_tooltip"]
        self._msg_drive = language_manager["main.source.tooltip.tooltip_drive"]
        self._msg_input = language_manager["global.status.message.input"]
        self._handler_tag = compose_tag(TAG_MAIN_SOURCE_TABLE_CHANNELS, SUF_HANDLER_REGISTRY)

        self.on_slot_toggled: Optional[SlotCallback] = None
        self.on_drive_changed: Optional[DriveCallback] = None

    @staticmethod
    def name_tag(channel_name: ChannelName) -> str:
        return compose_tag(PRE_MAIN_SOURCE_CHANNEL, channel_name, SUF_TEXT)

    @staticmethod
    def box_tag(channel_name: ChannelName, field: SettingsField) -> str:
        return compose_tag(PRE_MAIN_SOURCE_CHANNEL, channel_name, field, SUF_CHECKBOX)

    @staticmethod
    def slider_tag(channel_name: ChannelName) -> str:
        return compose_tag(PRE_MAIN_SOURCE_CHANNEL, channel_name, SUF_SLIDER)

    def create(self, view_model: SourceSettingsPanelViewModel) -> None:
        """Build the heading naming each column, then one line per channel under it."""
        with dpg.item_handler_registry(tag=self._handler_tag):
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_drive_released)

        with dpg.table(
            tag=TAG_MAIN_SOURCE_TABLE_CHANNELS,
            header_row=False,
            policy=dpg.mvTable_SizingFixedFit,
            resizable=False,
        ):
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.name_column_width)
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.choice_column_width)
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self._layout.choice_column_width)
            dpg.add_table_column(width_stretch=True)
            self._create_heading()
            for channel in view_model.channels:
                self._create_line(channel)

    def render(self, view_model: SourceSettingsPanelViewModel) -> None:
        """Draw what the inspected recordings say about each channel onto the line standing for it."""
        for channel in view_model.channels:
            self._render_line(channel, live=view_model.live)

    def _create_heading(self) -> None:
        """The column names above the lines, set small so the channels below carry the card."""
        with dpg.table_row():
            dpg.add_spacer(width=0)
            self._create_column_name(self._lbl_on)
            bend = self._create_column_name(self._lbl_bend)
            show_tooltip(
                bend, self._msg_bend, tag=compose_tag(TAG_MAIN_SOURCE_TABLE_CHANNELS, SUF_HEADING, SUF_TOOLTIP)
            )
            self._create_column_name(self._lbl_drive)

    @staticmethod
    def _create_column_name(label: str) -> int:
        text = dpg.add_text(label)
        FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)
        ThemeRegistry.get(TAG_GLOBAL_THEME_STEMS_SLOT_LABEL).bind_to_item(text)
        return int(text)

    def _create_line(self, channel: ChannelSettingsViewModel) -> None:
        channel_name = channel.channel
        with dpg.table_row():
            name = dpg.add_text(channel_label(self._language_manager, channel_name), tag=self.name_tag(channel_name))
            FontRegistry.bind_to_item(name, Font.BOLD_SMALL)
            self._create_box(channel_name, SettingsField.CHANNELS)
            if channel.bendable:
                self._create_box(channel_name, SettingsField.BENDS)
            else:
                dpg.add_spacer(width=0)

            self._create_slider(channel_name)

        self._render_line(channel, live=True)

    def _create_box(self, channel_name: ChannelName, field: SettingsField) -> None:
        dpg.add_checkbox(
            tag=self.box_tag(channel_name, field),
            user_data=(field, channel_name),
            callback=self._on_box,
        )

    def _create_slider(self, channel_name: ChannelName) -> None:
        slider_tag = self.slider_tag(channel_name)
        dpg.add_slider_float(
            tag=slider_tag,
            min_value=MIN_DRIVE,
            max_value=MAX_DRIVE,
            clamped=True,
            width=-1,
            format=self._layout.drive_format,
            user_data=channel_name,
        )
        FontRegistry.bind_to_item(slider_tag, Font.MONO_SMALL)
        dpg.bind_item_handler_registry(slider_tag, self._handler_tag)
        self._status_bar.bind_to_item(slider_tag, self._msg_input)
        show_tooltip(slider_tag, self._msg_drive, tag=compose_tag(slider_tag, SUF_TOOLTIP))

    def _render_line(self, channel: ChannelSettingsViewModel, *, live: bool) -> None:
        """Draw one channel's line: its name, its boxes and its drive, in the tone its reading takes."""
        channel_name = channel.channel
        ThemeRegistry.get(self._line_theme(channel, Agreement.ALL)).bind_to_item(self.name_tag(channel_name))
        self._render_box(channel, SettingsField.CHANNELS, channel.use, enabled=live)
        if channel.bendable:
            self._render_box(channel, SettingsField.BENDS, channel.bend, enabled=live and channel.bend_offered)

        self._render_slider(channel, enabled=live and channel.used)

    def _render_box(
        self,
        channel: ChannelSettingsViewModel,
        field: SettingsField,
        agreement: Agreement,
        *,
        enabled: bool,
    ) -> None:
        box_tag = self.box_tag(channel.channel, field)
        dpg_set_value(box_tag, agreement.reads_held)
        dpg_configure_item(box_tag, enabled=enabled)
        ThemeRegistry.get(self._line_theme(channel, agreement)).bind_to_item(box_tag)

    def _render_slider(self, channel: ChannelSettingsViewModel, *, enabled: bool) -> None:
        """Draw the channel's drive, leaving a slider the reader is holding as they hold it.

        A reading the recordings differ on states so in place of a value, with the grab resting at
        the calibrated level, and the first drag settles every recording on the value it reaches.
        """
        slider_tag = self.slider_tag(channel.channel)
        if not dpg.is_item_active(slider_tag):
            dpg_set_value(slider_tag, channel.drive_shown)

        drive_format = self._lbl_mixed if channel.drive_mixed else self._layout.drive_format
        dpg_configure_item(slider_tag, enabled=enabled, format=drive_format)
        theme = self._line_theme(channel, Agreement.SOME if channel.drive_mixed else Agreement.ALL)
        ThemeRegistry.get(theme).bind_to_item(slider_tag)

    @staticmethod
    def _line_theme(channel: ChannelSettingsViewModel, agreement: Agreement) -> str:
        """The tone a control on a line takes: muted where no recording uses the channel, softened
        where the recordings differ, and the channel's own color otherwise."""
        if not channel.used:
            return TAG_GLOBAL_THEME_CHANNEL_MUTED

        if agreement is Agreement.SOME:
            return PARTIAL_CHANNEL_THEME_TAGS[channel.channel]

        return CHANNEL_THEME_TAGS[channel.channel]

    def _on_box(self, _sender: Sender, _value: bool, user_data: Tuple[SettingsField, ChannelName]) -> None:
        field, channel_name = user_data
        self.call(self.on_slot_toggled, field, channel_name)

    def _on_drive_released(self, _sender: Sender, slider: Sender) -> None:
        """Report the drive a released slider holds, to the decimals the slider prints.

        The slider's clamp holds a typed value within the bounds a drive has, and rounding sets
        aside the single-precision noise the widget carries its value in.
        """
        channel_name: ChannelName = dpg.get_item_user_data(slider)
        drive = round(float(dpg.get_value(slider)), self._layout.drive_decimals)
        self.call(self.on_drive_changed, channel_name, drive)
