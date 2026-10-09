from pydantic import BaseModel

from sampletones_application.layout.primitives import DialogGeometry


class DisplaySettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: DialogGeometry
    countdown: DialogGeometry
