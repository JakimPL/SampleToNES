from dataclasses import dataclass
from typing import Final, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName

NO_RESERVE: Final[int] = 0
NO_INDENT: Final[int] = 0
COLUMN_BORDER: Final[int] = 1
ONE_SLOT: Final[int] = 1
TWO_SLOTS: Final[int] = 2


@dataclass(frozen=True)
class StemsColumns:
    """The columns every table of a stems grid stands in.

    A list draws one table per band, one for each run of rows a folder breaks, one inside each open
    folder, and one for the heading above them all; the settings card draws one row of the same
    grid. The reader meets them as a single grid because each declares these columns in the same
    order at the same widths, which is why this declaration stands in one place and every table
    asks it.

    The name column is the one that stretches, so a wider card spends its room on the recordings
    rather than on the boxes beside them. A channel column holds one box, or two where ``bends``
    states that a cell carries the bend on its channel, and takes the width that fits.

    ``folders`` states that the list this grid belongs to holds folders, which settles both ends
    of the row. At the right, a folder draws its recordings inside a region of their own, and the
    room that region spends there is held clear out here so the columns around a folder stand where
    the columns inside it stand. At the left, a folder's own row leads with the marker that opens
    it, and a row carrying none opens where that marker's glyph does.
    """

    layout: StemsListLayout
    channels: Tuple[ChannelName, ...]
    master: bool
    removable: bool
    bends: bool
    folders: bool

    @property
    def channel_width(self) -> int:
        """The room one channel's column takes, which the boxes standing in it decide."""
        return self.layout.channel_column_width if self.bends else self.layout.channel_solo_width

    @property
    def reserve(self) -> int:
        """The room a folder's region spends at the right of the grid, held clear across the list.

        A region insets its body by the well's padding and keeps a scrollbar's width clear beside
        it, so a strip of that width at the right end of every table outside a folder stands the
        two grids in one.
        """
        if not self.folders:
            return NO_RESERVE

        return self.layout.well_padding + self.layout.scrollbar_width

    @property
    def reserve_width(self) -> int:
        """The width the reserve column is declared at, so the room it holds is the region's.

        A column takes its own width plus the padding on either side of its cell and the rule drawn
        beside it, so those come off the room the strip is meant to hold clear.
        """
        return self.reserve - 2 * self.layout.cell_padding - COLUMN_BORDER

    def declare(self) -> None:
        """Add this grid's columns to the table currently being built."""
        if self.master:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self.layout.master_column_width)

        dpg.add_table_column(width_stretch=True)
        for _channel_name in self.channels:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self.channel_width)

        if self.removable:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self.layout.remove_button_width)

        if self.reserve_width > 0:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=self.reserve_width)

    def slots(self, channel_name: ChannelName) -> int:
        """How many boxes one channel's cell holds: the channel it takes, and the bend on it.

        A bend moves a note by a fraction of the divider its channel loads, so a channel whose
        periods stand at fixed distances holds the first slot alone.
        """
        if self.bends and channel_name in TONE_CHANNELS:
            return TWO_SLOTS

        return ONE_SLOT

    def box_indent(self, channel_name: ChannelName) -> int:
        """How far a channel's boxes sit in, so they stand in the middle of their own column."""
        return self._centered(self.slots(channel_name) * self.layout.channel_box_width)

    def marker_indent(self, glyph: str, font: Font) -> int:
        """How far a row carrying no marker sits in, so its name opens where a marker's glyph does.

        A folder's row leads with a button as wide as the marker column, and the glyph inside it
        stands in the middle of that button. A recording standing loose in the same list opens at
        the glyph rather than at the button, which reads as one column of names without spending
        the marker's whole width on a row that has none.
        """
        if not self.folders:
            return NO_INDENT

        measured = dpg.get_text_size(glyph, font=FontRegistry.get_tag(font))
        if measured is None:
            return NO_INDENT

        return max(NO_INDENT, (self.layout.twisty_width - int(measured[0])) // 2)

    def name_indent(self, label: str, font: Font) -> int:
        """How far a channel's name sits in, so it stands over the middle of its own column.

        The name is measured in the face it is drawn in, so a column reads as one thing however
        long the channel is called.
        """
        measured = dpg.get_text_size(label, font=FontRegistry.get_tag(font))
        if measured is None:
            return 0

        return self._centered(int(measured[0]))

    def open_leading_cells(self) -> None:
        """Open the cells standing before the channels, which a heading leaves blank."""
        if self.master:
            dpg.add_spacer()

        dpg.add_spacer()

    def open_trailing_cell(self) -> None:
        """Open the cell standing after the channels, which a heading leaves blank."""
        if self.removable:
            dpg.add_spacer()

    def _centered(self, span: int) -> int:
        """The indent standing something of this width in the middle of a channel's column."""
        return max(0, (self.channel_width - self.layout.cell_padding * 2 - span) // 2)
