from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class SettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: Dimensions
    combo_width: int
    label_width: int
