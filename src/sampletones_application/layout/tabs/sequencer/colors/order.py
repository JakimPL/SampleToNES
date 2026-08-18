from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class OrderColors(BaseModel, extra="forbid", frozen=True):
    """Colours specific to the order table: the row-label column, the master row and
    the divider below it, and the per-column highlights for the current and playing
    positions.
    """

    label: WrittenColor
    master: WrittenColor
    master_divider: WrittenColor
    column_current: WrittenColor
    column_playing: WrittenColor
