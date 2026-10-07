from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.ui.elements.fonts.font import Font
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.types.application import Sender


def add_empty_cell(row_id: Sender) -> None:
    """Fills a table cell that carries nothing, which keeps the cells after it in their columns."""
    empty_cell = dpg.add_table_cell(parent=row_id)
    if dpg.does_item_exist(empty_cell):
        dpg.add_spacer(parent=empty_cell, width=0)


def add_slot_group(row_id: Sender) -> Sender:
    """Opens a column's cell on a row, as the line its three slots are placed side by side in."""
    cell = dpg.add_table_cell(parent=row_id)
    group: Sender = dpg.add_group(
        horizontal=True,
        horizontal_spacing=0,
        parent=cell,
    )
    return group


def slot_font(channel: Optional[ChannelName]) -> Font:
    """The font a column's slots are drawn in: the Sample column's in bold, a channel's plain."""
    return Font.MONO_BOLD_SMALL if channel is None else Font.MONO_SMALL
