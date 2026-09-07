from pydantic import BaseModel


class StemsListLayout(BaseModel, extra="forbid", frozen=True):
    master_column_width: int
    channel_column_width: int
    channel_solo_width: int
    channel_box_width: int
    remove_button_width: int
    level_strip_height: int
    well_padding: int
    well_margin: int
    well_ceiling: int
    twisty_width: int
    folder_ceiling: int
    folder_indent: int
    window_overscan: int
    scrollbar_width: int
    cell_padding: int
    name_height: int
