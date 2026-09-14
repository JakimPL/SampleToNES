from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class NSFSettingsLayout(BaseModel, extra="forbid", frozen=True):
    """The NSF export dialog's geometry.

    Attributes:
        window: The dialog's size, its height a floor the content grows past.
        text_width: The width of a header text field, negative to leave its byte count room at the
            row's end.
        frame_width: The width of the field a repeat's order frame is typed into.
    """

    window: Dimensions
    text_width: int
    frame_width: int
