from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions
from sampletones_application.layout.settings.master_gain import MasterGainLayout


class AudioSettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: Dimensions
    master_gain: MasterGainLayout
