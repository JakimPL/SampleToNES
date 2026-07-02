from pydantic import BaseModel, ConfigDict

from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_yaml


class ModuleConfig(BaseModel):
    """Module identity and playback settings that shape the exported ``.ftm``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    author: str
    tempo: int
    speed: int
    nes_frequency: int


def load_module_config(path: Pathlike) -> ModuleConfig:
    return ModuleConfig.model_validate(load_yaml(path))
