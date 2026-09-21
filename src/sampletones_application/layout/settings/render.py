from pydantic import BaseModel

from sampletones_application.layout.primitives import DialogGeometry


class RenderSettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: DialogGeometry
