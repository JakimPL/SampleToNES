from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class FavoriteColors(BaseModel, extra="forbid", frozen=True):
    default: WrittenColor
    child: WrittenColor
