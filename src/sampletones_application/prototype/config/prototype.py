from pydantic import BaseModel

from sampletones_application.prototype.config.constraints import PrototypeConstraints
from sampletones_application.prototype.config.layout import PrototypeLayout


class PrototypeConfig(BaseModel, frozen=True):
    layout: PrototypeLayout
    constraints: PrototypeConstraints
