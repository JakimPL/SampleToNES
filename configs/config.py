from pydantic import BaseModel, ConfigDict, Field

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
