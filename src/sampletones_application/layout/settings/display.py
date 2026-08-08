from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class DisplaySettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: Dimensions
    countdown: Dimensions
