from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class RowColors(BaseModel, extra="forbid", frozen=True):
    """Colours marking where a tracker row falls in the pulse of the pattern.

    ``beat`` lifts the row that opens each beat off the zebra stripe and ``bar`` marks the
    row that opens each bar more strongly, so a long pattern reads as a rhythm at a glance.
    """

    beat: WrittenColor
    bar: WrittenColor
