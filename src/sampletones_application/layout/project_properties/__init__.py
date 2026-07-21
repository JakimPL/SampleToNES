from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class ProjectPropertiesLayout(BaseModel, extra="forbid", frozen=True):
    window: Dimensions
    label_width: int
    input_width: int
    comment_height: int
