from pathlib import Path

from pydantic import BaseModel

from sampletones_core.constants.enums import SpectrumMethod


class AudioSettingsUpdate(BaseModel, frozen=True):
    normalize: bool
    quantize: bool


class LibrarySettingsUpdate(BaseModel, frozen=True):
    sample_rate: int
    nes_frequency: int


class GenerationSettingsUpdate(BaseModel, frozen=True):
    """What the settings card reports for the whole run, whichever row it is editing."""

    drive: float


class AdvancedSettingsUpdate(BaseModel, frozen=True):
    max_workers: int
    spectrum_method: SpectrumMethod
    transformation_gamma: int
    library_directory: Path
    reconstructions_directory: Path
