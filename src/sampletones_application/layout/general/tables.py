from pydantic import BaseModel

from sampletones_application.layout.primitives import Padding


class TablesLayout(BaseModel, extra="forbid", frozen=True):
    label_width: int
    cell_padding: Padding
    frame_rounding: int
