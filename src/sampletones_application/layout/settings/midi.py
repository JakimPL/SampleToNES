from pydantic import BaseModel

from sampletones_application.layout.primitives import DialogGeometry


class MidiSettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: DialogGeometry
