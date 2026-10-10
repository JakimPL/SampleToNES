from typing import Dict, Final, FrozenSet, Optional, Tuple

import dearpygui.dearpygui as dpg

from automation.dearpygui.bridge import Bridge
from automation.dearpygui.geometry import Point, Rect
from automation.dearpygui.hand import Hand
from automation.dearpygui.items.colors import read_theme_text_color
from automation.dearpygui.items.reading import read_item
from automation.dearpygui.items.regions import read_region_view
from automation.dearpygui.items.texts import read_label
from automation.dearpygui.items.types import Item
from automation.dearpygui.keys import IMGUI_LEFT_SHIFT
from automation.dearpygui.reach import UnreachableError
from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_TRACKER_INPUT_OCTAVE,
    TAG_SEQUENCER_TRACKER_TABLE,
)
from sampletones_application.ui.elements.table.caret import CaretOverlay
from sampletones_application.ui.panels.sequencer.columns import (
    tracker_table_column,
)
from sampletones_application.view_model.sequencer.slot import SUBCOLUMNS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName

HEADER_ROW: Final[int] = 0
CELL_GROUP: Final[int] = 0
NUMBER_CELL: Final[int] = 1
NUMBER_LABEL: Final[int] = 0
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
    return _slot(frame_table_row(row), channel, subcolumn)


def _table_rows() -> Tuple[Item, ...]:
    """Every row the tracker's table holds, the header first. Runs on the render thread."""
    return tuple(dpg.get_item_children(TAG_SEQUENCER_TRACKER_TABLE, 1))


def frame_rows() -> Dict[int, int]:
    """Where each pattern row of the shown frame stands among the table's rows, by its index. Runs on the render
    thread.
    """
    rows: Dict[int, int] = {}
    for index, table_row in enumerate(_table_rows()):
        row = dpg.get_item_user_data(table_row)
        if isinstance(row, int):
            rows[row] = index

    return rows


def _number(table_index: int) -> Item:
    """The row-number label of the table's ``table_index``-th row. Runs on the render thread."""
    cell = dpg.get_item_children(_table_rows()[table_index], 1)[NUMBER_CELL]
    label: Item = dpg.get_item_children(cell, 1)[NUMBER_LABEL]
    return label


def _slot(table_index: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> Item:
    """The selectable drawing one slot of the table's ``table_index``-th row. Runs on the render thread."""
    table_row = _table_rows()[table_index]
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
        """Whether the caret stands in ``channel``'s cell on ``row``, as the box drawn over the grid shows it."""
        return self._bridge.ask(_caret_cell) == (row, channel)

    def caret_box(self) -> Optional[Rect]:
        """Where the caret's mark stands on the screen, while it shows one."""
        return self._bridge.ask(caret_mark)

    def caret_row(self, channel: Optional[ChannelName]) -> Optional[int]:
        """The pattern row the caret stands on in ``channel``'s column, if it stands in that column."""
        cell = self._bridge.ask(_caret_cell)
        if cell is None or cell[1] != channel:
            return None

        return cell[0]

    def is_row_tinted(self, row: int) -> bool:
        """Whether the row carries a background, as a beat, a bar, the caret's row or the playing row does."""
        return bool(
            self._bridge.ask(lambda: dpg.is_table_row_highlighted(TAG_SEQUENCER_TRACKER_TABLE, frame_table_row(row)))
        )

    def centered_row(self) -> Optional[int]:
        """The pattern row whose middle stands on the band's middle, within half a row, if one does.

        The band is the part of the grid the header leaves in view, and only a row drawn in the last
        frame is read.
        """

        def read() -> Optional[int]:
            band = read_region_view(TAG_SEQUENCER_TRACKER_TABLE)
            if band is None:
                return None

            middle = band.y + band.height * HALF
            for row, table_index in frame_rows().items():
                number = read_item(_number(table_index))
                if number.rect is None or not number.visible:
                    continue

                if abs(number.rect.y + number.rect.height * HALF - middle) <= number.rect.height * HALF:
                    return row

            return None

        return self._bridge.ask(read)

    def rows_above_the_frame(self) -> int:
        """How many rows stand between the header and the frame's first row."""
        return self._bridge.ask(lambda: frame_table_row(0) - (HEADER_ROW + 1))

    def numbers_above(self, count: int) -> Tuple[str, ...]:
        """What the row numbers of the ``count`` rows nearest above the frame read, top to bottom."""

        def read() -> Tuple[str, ...]:
            first = frame_table_row(0)
            return tuple(read_label(_number(index)) for index in range(first - count, first))

        return self._bridge.ask(read)

    def numbers_below(self, count: int) -> Tuple[str, ...]:
        """What the row numbers of the ``count`` rows nearest below the frame read, top to bottom."""

        def read() -> Tuple[str, ...]:
            last = max(frame_rows().values())
            return tuple(read_label(_number(index)) for index in range(last + 1, last + 1 + count))

        return self._bridge.ask(read)

    def number_color(self, row: int) -> Optional[Tuple[float, ...]]:
        """The color the row number of a pattern row of the frame is drawn in."""
        return self._bridge.ask(lambda: _theme_color(_number(frame_table_row(row))))

    def number_color_above(self, offset: int) -> Optional[Tuple[float, ...]]:
        """The color the row number standing ``offset`` rows above the frame's first row is drawn in."""
        return self._bridge.ask(lambda: _theme_color(_number(frame_table_row(0) - offset)))

    def click_above(self, offset: int, channel: Optional[ChannelName], subcolumn: SubColumn) -> None:
        """Clicks one slot of the row standing ``offset`` rows above the frame's first row."""
        item = self._bridge.ask(lambda: _slot(frame_table_row(0) - offset, channel, subcolumn))
        self._hand.scroll_into_view(item)
        self._hand.click(item)

    def tinted_rows_in_view(self) -> FrozenSet[int]:
        """The pattern rows drawn in the last frame that carry a background, by their index."""

        def read() -> FrozenSet[int]:
            return frozenset(
                row
                for row, table_index in frame_rows().items()
                if read_item(_number(table_index)).visible
                and dpg.is_table_row_highlighted(TAG_SEQUENCER_TRACKER_TABLE, table_index)
            )

        return self._bridge.ask(read)

    def octave(self) -> int:
        """The octave the octave field holds."""
        return int(self._bridge.ask(lambda: dpg.get_value(TAG_SEQUENCER_TRACKER_INPUT_OCTAVE)))

    def raise_octave(self) -> None:
        """Clicks the plus at the right end of the octave field, a square as tall as the field."""
        box = self._bridge.ask(lambda: read_item(TAG_SEQUENCER_TRACKER_INPUT_OCTAVE).rect)
        if box is None:
            raise UnreachableError("The octave field reports no box")

        self._hand.click_at(
            Point(
                x=round(box.x + box.width - box.height * HALF),
                y=round(box.y + box.height * HALF),
            )
        )


def _theme_color(item: Item) -> Optional[Tuple[float, ...]]:
    """The text color the theme bound to ``item`` sets. Runs on the render thread."""
    theme = dpg.get_item_info(item)["theme"]
    return read_theme_text_color(theme) if theme is not None else None


def _caret_cell() -> Optional[Tuple[int, Optional[ChannelName]]]:
    """The pattern row and the column the caret's box stands in, while it shows one. Runs on the render thread.

    The caret is a box drawn over the grid, and a table reports a highlighted column for every cell
    in it, so the box is what says where the caret stands. A cell spans its three slots.
    """
    middle = _caret_middle()
    if middle is None:
        return None

    x, y = middle
    for row, table_index in frame_rows().items():
        number = read_item(_number(table_index))
        if number.rect is None or not number.visible or not number.rect.y <= y < number.rect.y + number.rect.height:
            continue

        for channel in CHANNEL_AXIS:
            first = read_item(_slot(table_index, channel, SUBCOLUMNS[0])).rect
            last = read_item(_slot(table_index, channel, SUBCOLUMNS[-1])).rect
            if first is not None and last is not None and first.x <= x < last.x + last.width:
                return row, channel

    return None


def caret_mark() -> Optional[Rect]:
    """The mark the caret overlay draws under the active character, while it shows one. Runs on the render thread."""
    rectangle = CaretOverlay._mark  # pylint: disable=protected-access
    if rectangle is None or not dpg.does_item_exist(rectangle):
        return None

    configuration = dpg.get_item_configuration(rectangle)
    if not configuration.get("show"):
        return None

    corner, far = configuration["pmin"], configuration["pmax"]
    return Rect(x=corner[0], y=corner[1], width=far[0] - corner[0], height=far[1] - corner[1])


def _caret_middle() -> Optional[Tuple[float, float]]:
    """The middle of the caret's mark, while it shows one. Runs on the render thread."""
    mark = caret_mark()
    if mark is None:
        return None

    return mark.x + mark.width * HALF, mark.y + mark.height * HALF
