from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class ConverterLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    button_height: int
    stem_selection: Dimensions
    stem_selection_footer: int
