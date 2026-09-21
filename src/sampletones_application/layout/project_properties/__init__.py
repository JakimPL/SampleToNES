from pydantic import BaseModel

from sampletones_application.layout.primitives import DialogGeometry


class ProjectPropertiesLayout(BaseModel, extra="forbid", frozen=True):
    window: DialogGeometry
    label_width: int
    input_width: int
    comment_height: int
