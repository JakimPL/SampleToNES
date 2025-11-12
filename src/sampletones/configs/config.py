from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from sampletones.utils.serialization import load_json, save_json

from .general import GeneralConfig
from .generation import GenerationConfig
from .library import LibraryConfig


class Config(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    general: GeneralConfig = Field(default_factory=GeneralConfig, description="Base configuration for audio processing")
    library: LibraryConfig = Field(default_factory=LibraryConfig, description="Configuration for the audio library")
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig, description="Configuration for generation processes"
    )

    @classmethod
    def load(cls, path: Path) -> "Config":
        config_dict = load_json(path)
        return cls(**config_dict)

    def save(self, path: Path) -> None:
        config_dict = self.model_dump()
        save_json(path, config_dict)
