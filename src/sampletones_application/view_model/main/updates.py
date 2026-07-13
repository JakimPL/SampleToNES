from pathlib import Path
from typing import List

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName, SpectrumMethod


class AudioSettingsUpdate(BaseModel, frozen=True):
    normalize: bool
    quantize: bool


class LibrarySettingsUpdate(BaseModel, frozen=True):
    sample_rate: int
    nes_frequency: int


class GenerationSettingsUpdate(BaseModel, frozen=True):
    drive: float
    generators: List[GeneratorName]


class AdvancedSettingsUpdate(BaseModel, frozen=True):
    max_workers: int
    spectrum_method: SpectrumMethod
    transformation_gamma: int
    library_directory: Path
    reconstructions_directory: Path
