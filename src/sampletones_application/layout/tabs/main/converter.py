from pydantic import BaseModel

from sampletones_application.layout.primitives import DialogGeometry


class ConverterLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    button_height: int
    stem_selection: DialogGeometry
    stem_selection_footer: int
    stem_selection_list: int
    scan: DialogGeometry
