from typing import Self

from pydantic import BaseModel, ConfigDict

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.corpus.paths import MODULE_CONFIG_PATH


class ModuleConfig(BaseModel):
    """Module identity and playback settings that shape the exported files."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    author: str
    tempo: int
    speed: int
    nes_frequency: int

    @classmethod
    def load(cls) -> Self:
        """The module settings the package ships."""
        return load_yaml_model(MODULE_CONFIG_PATH, cls)
