from typing import FrozenSet

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import channel_label
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_HEADING,
    SUF_TABLE,
    SUF_TEXT,
    SUF_TOOLTIP,
    TAG_GLOBAL_THEME_CHANNEL_MUTED,
    TAG_GLOBAL_THEME_STEMS_SLOT_LABEL,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.stems.columns import StemsColumns
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName


class StemsHeading:
    """The channels a stems grid stands under, named once above the rows.

    Naming a channel here leaves each cell below free for the boxes it holds, and the cell reads as
    one channel because the name spans it. Where a cell holds two boxes, a second line names them:
    the channel the recording takes, and the bend on it.
    """

    def __init__(
        self,
        *,
        prefix: str,
        layout: StemsListLayout,
        language_manager: LanguageManager,
        bends: bool,
    ) -> None:
        self._prefix = prefix
        self._layout = layout
        self._language_manager = language_manager
        self._bends = bends
        self._lbl_on = language_manager["global.stems.label.channel_on"]
        self._lbl_bend = language_manager["global.stems.label.channel_bend"]
        self._msg_bend = language_manager["global.stems.message.bend_tooltip"]
        self._columns = StemsColumns(
            layout=layout,
            channels=(),
            master=False,
            removable=False,
            bends=bends,
            folders=False,
        )

    @property
    def table(self) -> str:
        """The table the channel names stand in, which is what lines them up with the rows."""
        return compose_tag(self._prefix, SUF_HEADING, SUF_TABLE)

    def name(self, channel_name: ChannelName) -> str:
        """The tag one channel's name carries."""
        return compose_tag(self._prefix, SUF_HEADING, channel_name, SUF_TEXT)

    def create(self, parent: str, columns: StemsColumns) -> None:
        """Draw the heading above the rows, in the columns those rows stand in.

        The grid below rules its own top edge, which is the line dividing the names from the rows
        they stand over.
        """
        self._columns = columns
        with dpg.table(
            tag=self.table,
            parent=parent,
            header_row=False,
            policy=dpg.mvTable_SizingFixedFit,
            resizable=False,
            borders_innerV=True,
        ):
            columns.declare()
            self._create_names()
            if self._bends:
                self._create_slots()

    def render(self, muted_channels: FrozenSet[ChannelName]) -> None:
        """Tone each channel's name the way its boxes are toned, so a column reads as one."""
        for channel_name in self._columns.channels:
            theme = (
                TAG_GLOBAL_THEME_CHANNEL_MUTED if channel_name in muted_channels else CHANNEL_THEME_TAGS[channel_name]
            )
            ThemeRegistry.get(theme).bind_to_item(self.name(channel_name))

    def _create_names(self) -> None:
        with dpg.table_row():
            self._columns.open_leading_cells()
            for channel_name in self._columns.channels:
                label = channel_label(self._language_manager, channel_name)
                name = dpg.add_text(
                    label,
                    tag=self.name(channel_name),
                    indent=self._columns.name_indent(label, Font.BOLD_SMALL),
                )
                FontRegistry.bind_to_item(name, Font.BOLD_SMALL)

            self._columns.open_trailing_cell()

    def _create_slots(self) -> None:
        """Label the slots a cell holds, each standing over the box it names."""
        with dpg.table_row():
            self._columns.open_leading_cells()
            for channel_name in self._columns.channels:
                self._create_channel_slots(channel_name)

            self._columns.open_trailing_cell()

    def _create_channel_slots(self, channel_name: ChannelName) -> None:
        with dpg.group(horizontal=True, indent=self._columns.box_indent(channel_name)):
            self._create_slot_label(self._lbl_on)
            if channel_name in TONE_CHANNELS:
                bend = self._create_slot_label(self._lbl_bend)
                show_tooltip(bend, self._msg_bend, tag=compose_tag(self.name(channel_name), SUF_TOOLTIP))

    def _create_slot_label(self, label: str) -> int:
        """One slot's name, held to the width of the box it stands over so the two line up."""
        with dpg.group():
            text = dpg.add_text(label)
            FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)
            ThemeRegistry.get(TAG_GLOBAL_THEME_STEMS_SLOT_LABEL).bind_to_item(text)
            dpg.add_spacer(width=self._layout.channel_box_width, height=0)

        return int(text)
