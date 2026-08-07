from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class TextColors(BaseModel, extra="forbid", frozen=True):
    default: WrittenColor
    disabled: WrittenColor
    error: WrittenColor
    highlight: WrittenColor
