from typing import Final, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.sequencer import TAG_SEQUENCER_TRACKER_INPUT_OCTAVE, TAG_SEQUENCER_TRACKER_TABLE
from sampletones_application.ui.panels.sequencer.columns import tracker_table_column
from sampletones_application.view_model.sequencer.slot import SUBCOLUMNS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.geometry import Point
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items.colors import read_theme_text_color
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.dearpygui.items.texts import read_label
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.dearpygui.keys import IMGUI_LEFT_SHIFT
from tests.suite.screens.dearpygui.reach import UnreachableError

HEADER_ROW: Final[int] = 0
CELL_GROUP: Final[int] = 0
HALF: Final[float] = 0.5


def frame_table_row(row: int) -> int:
    """Where a pattern row of the shown frame stands among the table's rows. Runs on the render thread.

    The table holds the header and the rows of the song either side of the frame as well, so a
    frame row is found by the pattern row it carries rather than by its place.

    Raises:
        UnreachableError: If the table holds no such row.
    """
    for index, table_row in enumerate(dpg.get_item_children(TAG_SEQUENCER_TRACKER_TABLE, 1)):
        if dpg.get_item_user_data(table_row) == row:
            return index

    raise UnreachableError(f"The tracker holds no row {row}")


def tracker_cell(row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> Item:
    """The selectable drawing one subcolumn of one channel's cell on a pattern row. Runs on the render thread.

    The Sample column stands for ``channel`` ``None``.
    """
    table_row = dpg.get_item_children(TAG_SEQUENCER_TRACKER_TABLE, 1)[frame_table_row(row)]
    cell = dpg.get_item_children(table_row, 1)[tracker_table_column(channel)]
    group = dpg.get_item_children(cell, 1)[CELL_GROUP]
    slot: Item = dpg.get_item_children(group, 1)[SUBCOLUMNS.index(subcolumn)]
    return slot


def tracker_cell_theme(row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> Optional[int]:
    """The theme the cell's text is drawn with, which cells of one kind and state share. Runs on the render thread."""
    theme = dpg.get_item_info(tracker_cell(row, channel, subcolumn))["theme"]
    return int(theme) if theme is not None else None


def _header_label(channel: Optional[ChannelName]) -> Item:
    """The name heading ``channel``'s column, the Sample column's for ``None``. Runs on the render thread."""
    table_row = dpg.get_item_children(TAG_SEQUENCER_TRACKER_TABLE, 1)[HEADER_ROW]
    cell = dpg.get_item_children(table_row, 1)[tracker_table_column(channel)]
    label: Item = dpg.get_item_children(cell, 1)[CELL_GROUP]
    return label


class Tracker:
    """The tracker grid: a row per pattern row, the Sample column and a column per channel, three slots to a cell.

    A cell's slots are the voice, the transpose and the volume, and a gesture names a slot by its
    row, its channel, or ``None`` for the Sample column, and its subcolumn.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def header(self, channel: Optional[ChannelName]) -> str:
        """What the header of ``channel``'s column reads, the Sample column's for ``None``."""
        return self._bridge.ask(lambda: read_label(_header_label(channel)))

    def click_header(self, channel: ChannelName) -> None:
        """Clicks the name heading ``channel``'s column, which mutes the channel or lets it sound again."""
        label = self._bridge.ask(lambda: _header_label(channel))
        self._hand.click(label)

    def text_color(self, row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> Optional[Tuple[float, ...]]:
        """The color one slot's text is drawn in, as the theme the slot wears sets it."""

        def read() -> Optional[Tuple[float, ...]]:
            theme = tracker_cell_theme(row, channel, subcolumn)
            return None if theme is None else read_theme_text_color(theme)

        return self._bridge.ask(read)

    def label(self, row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> str:
        """What one slot reads."""
        return self._bridge.ask(lambda: read_label(tracker_cell(row, channel, subcolumn)))

    def labels(self, row: int, channel: Optional[ChannelName]) -> Tuple[str, ...]:
        """What the three slots of one cell read, voice first."""
        return tuple(self.label(row, channel, subcolumn) for subcolumn in SUBCOLUMNS)

    def theme(self, row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> Optional[int]:
        """The theme one slot's text wears, or ``None`` while it wears none."""
        return self._bridge.ask(lambda: tracker_cell_theme(row, channel, subcolumn))

    def click(self, row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> None:
        """Clicks one slot, which puts the caret there."""
        item = self._bridge.ask(lambda: tracker_cell(row, channel, subcolumn))
        self._hand.scroll_into_view(item)
        self._hand.click(item)

    def hover(self, row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> None:
        """Rests the pointer on one slot, which the status bar then describes."""
        item = self._bridge.ask(lambda: tracker_cell(row, channel, subcolumn))
        self._hand.scroll_into_view(item)
        self._hand.hover(item)

    def leave(self) -> None:
        """Rests the pointer on the octave field above the grid, away from every slot."""
        self._hand.hover(TAG_SEQUENCER_TRACKER_INPUT_OCTAVE)

    def shift_click(self, row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> None:
        """Clicks one slot holding Shift, which stretches the block from the caret to it."""
        item = self._bridge.ask(lambda: tracker_cell(row, channel, subcolumn))
        self._hand.scroll_into_view(item)
        self._hand.click_holding(item, [IMGUI_LEFT_SHIFT])

    def right_click(self, row: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> None:
        """Clicks one slot with the right button, which opens its menu."""
        item = self._bridge.ask(lambda: tracker_cell(row, channel, subcolumn))
        self._hand.scroll_into_view(item)
        self._hand.right_click(item)

    def has_caret(self, row: int, channel: Optional[ChannelName]) -> bool:
        """Whether the caret stands in ``channel``'s cell on ``row``."""
        return bool(
            self._bridge.ask(
                lambda: dpg.is_table_cell_highlighted(
                    TAG_SEQUENCER_TRACKER_TABLE, frame_table_row(row), tracker_table_column(channel)
                )
            )
        )

    def is_row_tinted(self, row: int) -> bool:
        """Whether the row carries a background, as a beat, a bar, the caret's row or the playing row does."""
        return bool(
            self._bridge.ask(lambda: dpg.is_table_row_highlighted(TAG_SEQUENCER_TRACKER_TABLE, frame_table_row(row)))
        )

    def octave(self) -> int:
        """The octave the octave field holds."""
        return int(self._bridge.ask(lambda: dpg.get_value(TAG_SEQUENCER_TRACKER_INPUT_OCTAVE)))

    def raise_octave(self) -> None:
        """Clicks the plus at the right end of the octave field, a square as tall as the field."""
        box = self._bridge.ask(lambda: read_item(TAG_SEQUENCER_TRACKER_INPUT_OCTAVE).rect)
        if box is None:
            raise UnreachableError("The octave field reports no box")

        self._hand.click_at(Point(x=round(box.x + box.width - box.height * HALF), y=round(box.y + box.height * HALF)))
