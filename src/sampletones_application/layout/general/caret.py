from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class CaretLayout(BaseModel, extra="forbid", frozen=True):
    """How the tracker's caret is drawn: the underline's height and color, and the color of the frame around the
    cell.
    """

    height: int
    color: WrittenColor
    frame: WrittenColor
