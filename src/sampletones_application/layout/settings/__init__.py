from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions
from sampletones_application.layout.settings.master_gain import MasterGainLayout


class SettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: Dimensions
    combo_width: int
    label_width: int
    master_gain: MasterGainLayout
