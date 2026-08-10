from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class SampleColors(BaseModel, extra="forbid", frozen=True):
    """Colours marking the tracker's sample column and the divider beside it."""

    column: WrittenColor
    divider: WrittenColor
