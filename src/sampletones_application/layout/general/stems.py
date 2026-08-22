from pydantic import BaseModel


class StemsListLayout(BaseModel, extra="forbid", frozen=True):
    channel_column_width: int
    remove_button_width: int
    level_strip_height: int
    well_padding: int
    well_margin: int
