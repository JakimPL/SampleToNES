from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class HeaderColors(BaseModel, extra="forbid", frozen=True):
    library: WrittenColor
    reconstruction: WrittenColor
