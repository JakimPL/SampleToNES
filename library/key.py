from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from configs.config import Config as Config
from configs.library import LibraryConfig
from constants.general import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from ffts.window import Window
from utils.serialization import hash_model


class LibraryKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_rate: int = Field(..., ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE, description="Sample rate of the audio")
    frame_length: int = Field(..., ge=1, description="Length of a single frame")
    window_size: int = Field(..., ge=1, description="Size of the FFT window")
    transformation_gamma: float = Field(..., ge=0.0, le=1.0, description="Gamma value for transformation")
    config_hash: str = Field(..., description="Hash of the configuration")

    @classmethod
    def create(cls, config: LibraryConfig, window: Window) -> Self:
        config_hash = hash_model(config)
        return cls(
            sample_rate=config.sample_rate,
            frame_length=window.frame_length,
            window_size=window.size,
            transformation_gamma=config.transformation_gamma,
            config_hash=config_hash,
        )

    @property
    def filename(self) -> str:
        return f"sr_{self.sample_rate}_fl_{self.frame_length}_ws_{self.window_size}_tg_{self.transformation_gamma}_{self.config_hash}.dat"
