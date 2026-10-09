from pydantic import BaseModel, Field


class LoadingIndicatorLayout(BaseModel, extra="forbid", frozen=True):
    """The turning ring's size, stated as factors of the font it is drawn in.

    DearPyGui draws the ring ``radius × font size × (1 − thickness / 4)`` pixels across and pads its
    box by the frame padding above and below, the same padding it sets text beside the ring down by.
    The ring sits level with a line of that font when ``radius × (1 − thickness / 4)`` equals one.
    """

    radius: float = Field(gt=0.0)
    thickness: float = Field(gt=0.0, lt=4.0)
