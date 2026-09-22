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
    TAG_GLOBAL_THEME_CHANNEL_MUTED,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.stems.columns import StemsColumns
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_core.constants.enums import ChannelName


class StemsHeading:
    """The channels a stems grid stands under, named once above the rows.

    Naming a channel here leaves each cell below free for the box it holds, and the cell reads as
    one channel because the name spans it.
    """

    def __init__(
        self,
        *,
        prefix: str,
        layout: StemsListLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._prefix = prefix
        self._language_manager = language_manager
        self._columns = StemsColumns.empty(layout)

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
