from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from sampletones.configs import LibraryConfig
from sampletones.constants.general import (
    MAX_SAMPLE_RATE,
    MAX_TRANSFORMATION_GAMMA,
    MIN_SAMPLE_RATE,
)
from sampletones.ffts import Window
from sampletones.utils import hash_model


class LibraryKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_rate: int = Field(..., ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE, description="Sample rate of the audio")
    frame_length: int = Field(..., ge=1, description="Length of a single frame")
    window_size: int = Field(..., ge=1, description="Size of the FFT window")
    transformation_gamma: int = Field(
        ...,
        ge=0,
        le=MAX_TRANSFORMATION_GAMMA,
        description="Gamma value for transformation",
    )
    config_hash: str = Field(..., description="Hash of the configuration")
    filename: str = Field(..., description="Filename representing the key")

    @classmethod
    def create(cls, config: LibraryConfig, window: Window) -> Self:
        config_hash = hash_model(config)
        filename = cls.get_filename(config, window, config_hash)
        return cls(
            sample_rate=config.sample_rate,
            frame_length=window.frame_length,
            window_size=window.size,
            transformation_gamma=config.transformation_gamma,
            config_hash=config_hash,
            filename=filename,
        )

    @staticmethod
    def get_filename(config: LibraryConfig, window: Window, config_hash: str) -> str:
        return f"sr_{config.sample_rate}_cr_{config.change_rate}_ws_{window.size}_tg_{config.transformation_gamma}_ch_{config_hash}.dat"
