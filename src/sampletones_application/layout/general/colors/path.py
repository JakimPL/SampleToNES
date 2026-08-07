from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class PathColors(BaseModel, extra="forbid", frozen=True):
    default: WrittenColor
    hover: WrittenColor
