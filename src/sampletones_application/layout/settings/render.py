from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class RenderSettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: Dimensions
