from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.configs import InstructionsLibraryConfig
from sampletones_core.constants.algorithm import MAX_TRANSFORMATION_GAMMA
from sampletones_core.constants.audio import AcceptedSampleRate
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.library.filename.fields import InstructionsFilenameFields
from sampletones_core.library.settings import LibrarySettings
from sampletones_shared.constants.nes import MAX_NES_FREQUENCY, MIN_NES_FREQUENCY
from sampletones_shared.utils.hashing import hash_model, hash_models


class InstructionLibraryKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_rate: AcceptedSampleRate = Field(
        ...,
        description="Sample rate of the audio",
    )
    nes_frequency: int = Field(
        ...,
        ge=MIN_NES_FREQUENCY,
        le=MAX_NES_FREQUENCY,
        description="Instruction change rate in Hz the library was built for",
    )
    frame_length: int = Field(..., ge=1, description="Length of a single frame")
    window_size: int = Field(..., ge=1, description="Size of the FFT window")
    transformation_gamma: int = Field(
        ...,
        ge=0,
        le=MAX_TRANSFORMATION_GAMMA,
        description="Gamma value for transformation",
    )
    spectrum_method: SpectrumMethod = Field(
        default=SpectrumMethod.FFT,
        description="Spectrum generation method",
    )
    config_hash: str = Field(..., description="Hash of the configuration")
    filename: str = Field(..., description="Filename representing the key")

    @classmethod
    def create(cls, settings: LibrarySettings, window: Window) -> InstructionLibraryKey:
        """The key of the library built under ``settings``.

        The hash covers the library section and the range of notes alike, so a library built for
        another range of notes is another file.
        """
        config = settings.library
        config_hash = hash_models(config, settings.pitch_range)
        filename = cls.get_filename(config, window, config_hash)
        return cls(
            sample_rate=config.sample_rate,
            nes_frequency=config.nes_frequency,
            frame_length=window.frame_length,
            window_size=window.size,
            transformation_gamma=config.transformation_gamma,
            spectrum_method=config.spectrum_method,
            config_hash=config_hash,
            filename=filename,
        )

    @classmethod
    def library_only_filename(cls, config: InstructionsLibraryConfig, window: Window) -> str:
        """The filename a library built under ``config`` was written as before library data version 2.2,
        whose hash covers the library section alone."""
        return cls.get_filename(config, window, hash_model(config))

    @staticmethod
    def get_filename(config: InstructionsLibraryConfig, window: Window, config_hash: str) -> str:
        return InstructionsFilenameFields(
            sr=config.sample_rate,
            nf=config.nes_frequency,
            ws=window.size,
            tg=config.transformation_gamma,
            sm=config.spectrum_method,
            ch=config_hash,
        ).filename
