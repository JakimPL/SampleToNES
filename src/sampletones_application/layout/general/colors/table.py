from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class TableColors(BaseModel, extra="forbid", frozen=True):
    label: WrittenColor
    value: WrittenColor
