from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.configs import InstructionsLibraryConfig
from sampletones_core.configs.config import Config
from sampletones_core.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from sampletones_core.constants.general import MAX_TRANSFORMATION_GAMMA
from sampletones_core.fft import Window
from sampletones_core.library.filename.fields import InstructionsFilenameFields
from sampletones_shared.utils.serialization import hash_model


class InstructionLibraryKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_rate: int = Field(
        ...,
        ge=MIN_SAMPLE_RATE,
        le=MAX_SAMPLE_RATE,
        description="Sample rate of the audio",
    )
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
    def from_config(cls, config: Config) -> InstructionLibraryKey:
        window = Window.from_config(config)
        return cls.create(config.library, window)

    @classmethod
    def create(cls, config: InstructionsLibraryConfig, window: Window) -> InstructionLibraryKey:
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
    def get_filename(config: InstructionsLibraryConfig, window: Window, config_hash: str) -> str:
        return InstructionsFilenameFields(
            sr=config.sample_rate,
            nf=config.nes_frequency,
            ws=window.size,
            tg=config.transformation_gamma,
            ch=config_hash,
        ).filename
