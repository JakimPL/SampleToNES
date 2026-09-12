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

    @property
    def folder_reserve(self) -> int:
        """The room a folder's region spends at the right of its body.

        A region insets its body by its padding and keeps a scrollbar's width clear beside it, so
        the grid outside a folder holds that same strip and the two grids stand as one.
        """
        return self.well_padding + self.scrollbar_width
