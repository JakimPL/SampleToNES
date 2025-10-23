from pydantic import BaseModel, Field

from configs.calculation import CalculationConfig
from configs.general import GeneralConfig
from configs.generation import GenerationConfig
from configs.library import LibraryConfig


class Config(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig, description="Base configuration for audio processing")
    library: LibraryConfig = Field(default_factory=LibraryConfig, description="Configuration for the audio library")
    calculation: CalculationConfig = Field(
        default_factory=CalculationConfig, description="Configuration for calculations"
    )
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig, description="Configuration for generation processes"
    )

    class Config:
        frozen = True
        arbitrary_types_allowed = True
