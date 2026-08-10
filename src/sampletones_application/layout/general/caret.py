from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class CaretLayout(BaseModel, extra="forbid", frozen=True):
    offset: int
    width_padding: int
    fill: WrittenColor
    border: WrittenColor
