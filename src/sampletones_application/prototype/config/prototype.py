from pydantic import BaseModel

from .constraints import PrototypeConstraints
from .layout import PrototypeLayout


class PrototypeConfig(BaseModel, frozen=True):
    layout: PrototypeLayout
    constraints: PrototypeConstraints
