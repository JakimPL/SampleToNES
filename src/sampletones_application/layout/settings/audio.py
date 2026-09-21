from pydantic import BaseModel

from sampletones_application.layout.primitives import DialogGeometry
from sampletones_application.layout.settings.master_gain import MasterGainLayout


class AudioSettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: DialogGeometry
    master_gain: MasterGainLayout
